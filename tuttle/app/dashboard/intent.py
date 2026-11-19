"""Business logic for the dashboard view."""

import datetime
from decimal import Decimal

from ...forecasting import (
    cash_flow_series,
    revenue_series,
)
from ...fx import primary_currency
from ...kpi import (
    compute_kpis,
    project_budget_status,
)
from ...model import Contract, FinancialGoal, Invoice, Project, RecurringExpense
from ...tax_reserves import convert_invoice, distinct
from ..core.abstractions import Intent, SQLModelDataSourceMixin
from ..core.intent_result import IntentResult, fails_with
from ..core.operating_country import OperatingCountryMixin
from ..timetracking.data_source import TimeTrackingDataFrameSource


class DashboardIntent(OperatingCountryMixin, SQLModelDataSourceMixin, Intent):
    """Gathers data for the freelance business dashboard."""

    def __init__(self):
        SQLModelDataSourceMixin.__init__(self)
        self._time_data_source = TimeTrackingDataFrameSource()

    @fails_with("Failed to compute KPIs", append_exception=True)
    def get_kpis(self) -> IntentResult:
        """Compute KPI summary from invoices, contracts, and calendar data."""
        invoices = self.query(Invoice)
        contracts = self.query(Contract)
        projects = self.query(Project)
        expenses = self.query(RecurringExpense)
        country = self._get_country()
        time_data = self._time_data_source.get_data_frame()
        kpis = compute_kpis(invoices, contracts, projects, country=country, time_data=time_data, expenses=expenses)
        return IntentResult(was_intent_successful=True, data=kpis)

    def get_revenue_series(self, granularity: str = "month", offset: int = 0) -> IntentResult:
        """Revenue per week/month/year bucket for one window of the revenue chart."""
        data = revenue_series(
            self.query(Invoice),
            self.query(Project),
            self._time_data_source.get_data_frame(),
            granularity=granularity,
            offset=int(offset),
            country=self._get_country(),
        )
        return IntentResult(was_intent_successful=True, data=data)

    def get_cash_flow(self, forecast_months: int = 6) -> IntentResult:
        """Get cash flow projection based on invoices, expenses, and calendar allocations."""
        invoices = self.query(Invoice)
        contracts = self.query(Contract)
        projects = self.query(Project)
        expenses = self.query(RecurringExpense)
        time_data = self._time_data_source.get_data_frame()
        country = self._get_country()

        data = cash_flow_series(
            invoices=invoices,
            contracts=contracts,
            projects=projects,
            expenses=expenses,
            time_data=time_data,
            forecast_months=int(forecast_months),
            country=country,
        )
        return IntentResult(was_intent_successful=True, data=data)

    @fails_with("Failed to load project budgets", append_exception=True)
    def get_project_budgets(self) -> IntentResult:
        """Budget utilization for all projects from calendar time-tracking data."""
        projects = self.query(Project)
        time_data = self._time_data_source.get_data_frame()
        data = project_budget_status(projects, time_data=time_data)
        return IntentResult(was_intent_successful=True, data=data)

    def _revenue_by_target_year(self, invoices, currency: str) -> tuple[dict, dict]:
        """Paid revenue, net of VAT, accumulated from Jan 1 of each year up to today.

        A goal is measured against its own target year, not the current one,
        so a goal due in a future year does not inherit this year's revenue.
        Returns the totals by year, and by year the invoices each leaves out
        for lack of an exchange rate.
        """
        today = datetime.date.today()
        totals: dict = {}
        left_out: dict = {}
        for inv in invoices:
            if not inv.is_counted or not inv.paid or inv.date > today:
                continue
            year = inv.date.year
            converted = convert_invoice(inv, currency, left_out.setdefault(year, []))
            if converted is None:
                # No resolvable FX rate — leave it out rather than count it as zero.
                continue
            totals[year] = totals.get(year, Decimal(0)) + converted[0] - converted[1]
        return totals, left_out

    @fails_with("Failed to load financial goals", append_exception=True)
    def get_financial_goals(self) -> IntentResult:
        """Load all financial goals with progress against their target year's revenue."""
        goals = self.query(FinancialGoal)
        invoices = self.query(Invoice)
        country = self._get_country()
        currency = primary_currency(country)
        revenue_by_year, left_out_by_year = self._revenue_by_target_year(invoices, currency)

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
                    "unconverted": distinct(left_out_by_year.get(g.target_date.year, [])),
                }
            )
        return IntentResult(was_intent_successful=True, data=goals_with_progress)

    @fails_with("Failed to save financial goal", append_exception=True)
    def save_financial_goal(self, goal: FinancialGoal) -> IntentResult:
        """Save a financial goal."""
        self.store(goal)
        return IntentResult(was_intent_successful=True, data=goal)

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

    @fails_with("Failed to delete financial goal", append_exception=True)
    def delete_financial_goal(self, goal_id: int) -> IntentResult:
        """Delete a financial goal by ID."""
        self.delete_by_id(FinancialGoal, goal_id)
        return IntentResult(was_intent_successful=True, data=None)
