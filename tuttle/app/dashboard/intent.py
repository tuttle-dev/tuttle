"""Business logic for the dashboard view."""

import datetime
from decimal import Decimal

from ...forecasting import (
    cash_flow_projection,
    monthly_revenue_from_calendar,
    revenue_curve_with_calendar,
    revenue_series,
)
from ...fx import primary_currency
from ...kpi import (
    compute_kpis,
    monthly_revenue_breakdown,
    monthly_spendable_breakdown,
    project_budget_status,
)
from ...model import Contract, FinancialGoal, Invoice, Project, User
from ...tax_reserves import convert_invoice
from ..core.abstractions import Intent, SQLModelDataSourceMixin
from ..core.intent_result import IntentResult
from ..timetracking.data_source import TimeTrackingDataFrameSource


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
        return ""

    def get_kpis(self) -> IntentResult:
        """Compute KPI summary from invoices, contracts, and calendar data."""
        try:
            invoices = self.query(Invoice)
            contracts = self.query(Contract)
            projects = self.query(Project)
            country = self._get_country()
            time_data = self._time_data_source.get_data_frame()
            kpis = compute_kpis(invoices, contracts, projects, country=country, time_data=time_data)
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
            data = monthly_revenue_breakdown(invoices, n_months=n_months, country=self._get_country())
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
            revenue = monthly_revenue_breakdown(invoices, n_months=n_months, country=country)
            spendable = monthly_spendable_breakdown(invoices, country=country, n_months=n_months)
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

    def get_revenue_series(self, granularity: str = "month", offset: int = 0) -> IntentResult:
        """Revenue per week/month/year bucket for one window of the revenue chart."""
        try:
            data = revenue_series(
                self.query(Invoice),
                self.query(Project),
                self._time_data_source.get_data_frame(),
                granularity=granularity,
                offset=int(offset),
                country=self._get_country(),
            )
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load revenue series: {e}",
                log_message=f"DashboardIntent.get_revenue_series: {e}",
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
            invoices = self.query(Invoice)
            contracts = self.query(Contract)
            projects = self.query(Project)
            time_data = self._time_data_source.get_data_frame()

            today = datetime.date.today()
            forecast_start = today.replace(day=1)
            forecast_end = (forecast_start + datetime.timedelta(days=30 * forecast_months)).replace(day=1)

            rev_forecast = monthly_revenue_from_calendar(time_data, projects, forecast_start, forecast_end, invoices=invoices)

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

    def _revenue_by_target_year(self, invoices, currency: str) -> dict:
        """Paid revenue accumulated from Jan 1 of each year up to today.

        A goal is measured against its own target year, not the current one,
        so a goal due in a future year does not inherit this year's revenue.
        """
        today = datetime.date.today()
        totals: dict = {}
        for inv in invoices:
            if inv.cancelled or not inv.paid or inv.date > today:
                continue
            converted = convert_invoice(inv, currency)
            if converted is None:
                # No resolvable FX rate — leave it out rather than count it as zero.
                continue
            year = inv.date.year
            totals[year] = totals.get(year, Decimal(0)) + converted[0]
        return totals

    def get_financial_goals(self) -> IntentResult:
        """Load all financial goals with progress against their target year's revenue."""
        try:
            goals = self.query(FinancialGoal)
            invoices = self.query(Invoice)
            country = self._get_country()
            currency = primary_currency(country)
            revenue_by_year = self._revenue_by_target_year(invoices, currency)

            goals_with_progress = []
            for g in goals:
                revenue = float(revenue_by_year.get(g.target_date.year, Decimal(0)))
                target = float(g.target_amount)
                progress = min(revenue / target, 1.0) if target > 0 else 0.0

                # A met goal is a historical fact: set the flag, never clear it.
                if progress >= 1.0 and not g.is_reached:
                    g.is_reached = True
                    self.store(g)

                goals_with_progress.append(
                    {
                        "goal": g,
                        "progress": progress,
                        "ytd_revenue": revenue,
                        "currency": currency,
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

    def save_financial_goal_from_dict(self, data: dict) -> IntentResult:
        """Create or update a financial goal from a plain dict."""
        clean = {k: v for k, v in data.items() if k != "id" and not k.startswith("_")}
        # The update path bypasses Pydantic validation, so coerce the date here.
        target_date = clean.get("target_date")
        if isinstance(target_date, str):
            clean["target_date"] = datetime.date.fromisoformat(target_date)

        goal_id = data.get("id")
        if goal_id:
            existing = next((g for g in self.query(FinancialGoal) if g.id == goal_id), None)
            if existing:
                for k, v in clean.items():
                    setattr(existing, k, v)
                return self.save_financial_goal(existing)
        return self.save_financial_goal(FinancialGoal(**clean))

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
