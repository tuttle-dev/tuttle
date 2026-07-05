"""Business logic for the dashboard view."""

import datetime

from ..core.abstractions import SQLModelDataSourceMixin, Intent
from ..core.intent_result import IntentResult
from ..timetracking.data_source import TimeTrackingDataFrameSource

from ...model import Contract, Invoice, Project, FinancialGoal, User
from ...kpi import (
    compute_kpis,
    monthly_revenue_breakdown,
    monthly_spendable_breakdown,
    project_budget_status,
)
from ...forecasting import (
    revenue_curve_with_calendar,
    cash_flow_projection,
    monthly_revenue_from_calendar,
)


class DashboardIntent(SQLModelDataSourceMixin, Intent):
    """Gathers data for the freelance business dashboard."""

    def __init__(self):
        SQLModelDataSourceMixin.__init__(self)
        self._time_data_source = TimeTrackingDataFrameSource()

    def _get_country(self) -> str:
        """Determine the user's operating country for tax purposes."""
        try:
            users = self.query(User)
            if users and users[0].operating_country:
                return users[0].operating_country
        except Exception:
            pass
        return "Germany"

    def get_kpis(self) -> IntentResult:
        """Compute KPI summary from invoices, contracts, and calendar data."""
        try:
            invoices = self.query(Invoice)
            contracts = self.query(Contract)
            projects = self.query(Project)
            country = self._get_country()
            time_data = self._time_data_source.get_data_frame()
            kpis = compute_kpis(
                invoices, contracts, projects, country=country, time_data=time_data
            )
            return IntentResult(was_intent_successful=True, data=kpis)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to compute KPIs: {e}",
                log_message=f"DashboardIntent.get_kpis: {e}",
                exception=e,
            )

    def get_monthly_revenue(self, n_months: int = 12) -> IntentResult:
        """Get monthly revenue breakdown for the last n months."""
        try:
            invoices = self.query(Invoice)
            data = monthly_revenue_breakdown(invoices, n_months=n_months)
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load monthly revenue: {e}",
                log_message=f"DashboardIntent.get_monthly_revenue: {e}",
                exception=e,
            )

    def get_monthly_spendable_income(self, n_months: int = 12) -> IntentResult:
        """Get monthly spendable income breakdown for the last n months."""
        try:
            invoices = self.query(Invoice)
            country = self._get_country()
            data = monthly_spendable_breakdown(
                invoices,
                country=country,
                n_months=n_months,
            )
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load monthly spendable income: {e}",
                log_message=f"DashboardIntent.get_monthly_spendable_income: {e}",
                exception=e,
            )

    def get_monthly_chart_data(self, n_months: int = 12) -> IntentResult:
        """Revenue + spendable in one query (avoids duplicate invoice loads)."""
        try:
            invoices = self.query(Invoice)
            country = self._get_country()
            revenue = monthly_revenue_breakdown(invoices, n_months=n_months)
            spendable = monthly_spendable_breakdown(
                invoices, country=country, n_months=n_months
            )
            return IntentResult(
                was_intent_successful=True,
                data={"revenue": revenue, "spendable": spendable},
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load chart data: {e}",
                log_message=f"DashboardIntent.get_monthly_chart_data: {e}",
                exception=e,
            )

    def get_revenue_curve(self, forecast_months: int = 6) -> IntentResult:
        """Get combined historical + calendar-based + contract-fallback revenue curve."""
        try:
            invoices = self.query(Invoice)
            contracts = self.query(Contract)
            projects = self.query(Project)
            time_data = self._time_data_source.get_data_frame()
            data = revenue_curve_with_calendar(
                invoices,
                contracts,
                projects,
                time_data,
                forecast_months=forecast_months,
            )
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to generate revenue forecast: {e}",
                log_message=f"DashboardIntent.get_revenue_curve: {e}",
                exception=e,
            )

    def get_cash_flow(self, forecast_months: int = 6) -> IntentResult:
        """Get cash flow projection based on calendar allocations."""
        try:
            contracts = self.query(Contract)
            projects = self.query(Project)
            time_data = self._time_data_source.get_data_frame()

            today = datetime.date.today()
            forecast_start = today.replace(day=1)
            forecast_end = (
                forecast_start + datetime.timedelta(days=30 * forecast_months)
            ).replace(day=1)

            rev_forecast = monthly_revenue_from_calendar(
                time_data, projects, forecast_start, forecast_end
            )

            data = cash_flow_projection(rev_forecast, contracts)
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to generate cash flow projection: {e}",
                log_message=f"DashboardIntent.get_cash_flow: {e}",
                exception=e,
            )

    def get_project_budgets(self) -> IntentResult:
        """Budget utilization for all projects from calendar time-tracking data."""
        try:
            projects = self.query(Project)
            time_data = self._time_data_source.get_data_frame()
            data = project_budget_status(projects, time_data=time_data)
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load project budgets: {e}",
                log_message=f"DashboardIntent.get_project_budgets: {e}",
                exception=e,
            )

    def get_financial_goals(self) -> IntentResult:
        """Load all financial goals with progress calculated against YTD revenue."""
        try:
            goals = self.query(FinancialGoal)
            invoices = self.query(Invoice)
            country = self._get_country()
            time_data = self._time_data_source.get_data_frame()
            kpis = compute_kpis(
                invoices,
                self.query(Contract),
                self.query(Project),
                country=country,
                time_data=time_data,
            )
            ytd_revenue = float(kpis.total_revenue_ytd)

            goals_with_progress = []
            for g in goals:
                target = float(g.target_amount)
                progress = min(ytd_revenue / target, 1.0) if target > 0 else 0.0
                goals_with_progress.append(
                    {
                        "goal": g,
                        "progress": progress,
                        "ytd_revenue": ytd_revenue,
                        "currency": kpis.tax_currency,
                    }
                )
            return IntentResult(was_intent_successful=True, data=goals_with_progress)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load financial goals: {e}",
                log_message=f"DashboardIntent.get_financial_goals: {e}",
                exception=e,
            )

    def save_financial_goal(self, goal: FinancialGoal) -> IntentResult:
        """Save a financial goal."""
        try:
            self.store(goal)
            return IntentResult(was_intent_successful=True, data=goal)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to save financial goal: {e}",
                log_message=f"DashboardIntent.save_financial_goal: {e}",
                exception=e,
            )

    def delete_financial_goal(self, goal_id: int) -> IntentResult:
        """Delete a financial goal by ID."""
        try:
            self.delete_by_id(FinancialGoal, goal_id)
            return IntentResult(was_intent_successful=True, data=None)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to delete financial goal: {e}",
                log_message=f"DashboardIntent.delete_financial_goal: {e}",
                exception=e,
            )
