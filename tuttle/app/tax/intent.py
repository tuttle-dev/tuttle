"""Business logic for the Tax view."""

import datetime
from decimal import Decimal

from ...forecasting import contracted_this_year
from ...fx import primary_currency
from ...model import Invoice, Project, RecurringExpense
from ...tax import (
    all_operating_countries,
    get_tax_system,
    has_tax_model,
    supported_countries,
)
from ...tax_reserves import (
    compute_income_tax_reserve,
    compute_spendable_income,
    distinct,
    monthly_vat_breakdown,
)
from ..core.abstractions import Intent, SQLModelDataSourceMixin
from ..core.intent_result import IntentResult, fails_with
from ..core.operating_country import OperatingCountryMixin
from ..timetracking.data_source import TimeTrackingDataFrameSource


class TaxIntent(OperatingCountryMixin, SQLModelDataSourceMixin, Intent):
    """Gathers tax-related data for the freelance tax planning view."""

    def __init__(self):
        SQLModelDataSourceMixin.__init__(self)
        self._time_data_source = TimeTrackingDataFrameSource()

    def _get_tax_currency(self, country: str) -> str:
        """The currency aggregates are shown in (settings, default: tax system)."""
        return primary_currency(country)

    def _contracted_this_year(self, year, invoices, projects, time_data, currency: str, left_out=None) -> Decimal:
        """Revenue committed contracts will still bring in from today to the end of the year."""
        if year is not None and year != datetime.date.today().year:
            return Decimal(0)
        return contracted_this_year(projects, invoices, time_data, currency=currency, left_out=left_out)

    @fails_with("Failed to compute spendable income", append_exception=True)
    def get_spendable_income(self, year: int | None = None) -> IntentResult:
        """Compute spendable income breakdown."""
        invoices = self.query(Invoice)
        expenses = self.query(RecurringExpense)
        projects = self.query(Project)
        country = self._get_country()
        currency = self._get_tax_currency(country)
        time_data = self._time_data_source.get_data_frame()
        left_out: list = []
        spending = compute_spendable_income(
            invoices,
            country,
            expenses=expenses,
            currency=currency,
            year=year,
            projects=projects,
            time_data=time_data,
            contracted=self._contracted_this_year(year, invoices, projects, time_data, currency, left_out),
            left_out=left_out,
        )
        data = {"spending": spending, "currency": currency}
        return IntentResult(was_intent_successful=True, data=data)

    @fails_with("Failed to compute income tax estimate", append_exception=True)
    def get_income_tax_estimate(self, year: int | None = None) -> IntentResult:
        """Get detailed income tax estimate with bracket info.

        Without tax rules for the country and year there is no estimate:
        ``tax_reserve`` is None and ``tax_unavailable_reason`` says why.
        """
        today = datetime.date.today()

        invoices = self.query(Invoice)
        expenses = self.query(RecurringExpense)
        projects = self.query(Project)
        country = self._get_country()
        currency = self._get_tax_currency(country)
        time_data = self._time_data_source.get_data_frame()
        spending = compute_spendable_income(
            invoices,
            country,
            expenses=expenses,
            currency=currency,
            year=year,
            projects=projects,
            time_data=time_data,
            contracted=self._contracted_this_year(year, invoices, projects, time_data, currency),
        )

        # tax_base, not taxable_profit: deductible dynamic expenses have already
        # been taken off, and charging them again here would double-count.
        total_income = spending.tax_base
        no_tax = spending.tax_unavailable_reason
        tax_reserve = None
        bracket_data = []
        if no_tax is None:
            tax_reserve = compute_income_tax_reserve(total_income, country, year=year, currency=currency)
            ref_date = datetime.date(year, 7, 1) if year else today
            bracket_data = self._compute_bracket_data(get_tax_system(country, date=ref_date), total_income)

        data = {
            "tax_reserve": tax_reserve,
            "income_basis": total_income,
            "received_net": spending.received_net,
            "outstanding_net": spending.outstanding_net,
            "planned_revenue": spending.planned_revenue,
            "contracted_revenue": spending.contracted_revenue,
            "deducted_expenses": spending.business_expenses + spending.dynamic_expenses_deductible,
            "brackets": bracket_data,
            "country": country,
            "country_supported": no_tax is None,
            "tax_unavailable_reason": no_tax,
            "currency": currency,
        }
        return IntentResult(was_intent_successful=True, data=data)

    @staticmethod
    def _compute_bracket_data(tax_system, income: Decimal) -> list:
        """Build bracket visualization data from the tax system's zone data."""
        zones = tax_system.bracket_info
        income_f = float(income)
        allowance = tax_system.params.basic_allowance
        brackets = []
        prev_end = 0
        for zone in zones:
            up_to = zone["up_to"]
            ztype = zone.get("type")
            if ztype == "zero":
                start = 0
                end = up_to
            elif tax_system.params.formula_type == "german_progressive":
                # §32a zones are bounded by absolute incomes
                start = prev_end
                end = up_to if up_to is not None else start + 100000
            else:
                # Marginal bracket zones: display bracket range offset by allowance
                start = prev_end + allowance if not brackets else prev_end
                end = (up_to + allowance) if up_to is not None else start + 100000
            brackets.append(
                {
                    "label": zone["label"],
                    "start": start,
                    "end": end,
                    "is_current": start <= income_f < (end if up_to is not None else float("inf")),
                }
            )
            prev_end = end
        return brackets

    @fails_with("Failed to get available years", append_exception=True)
    def get_available_years(self) -> IntentResult:
        """Return the current year and every year with issued invoices, descending."""
        invoices = self.query(Invoice)
        years = sorted(
            {inv.date.year for inv in invoices if inv.is_counted} | {datetime.date.today().year},
            reverse=True,
        )
        return IntentResult(was_intent_successful=True, data=years)

    def supported_countries(self) -> IntentResult:
        """Return list of countries with tax system support."""
        return IntentResult(was_intent_successful=True, data=supported_countries())

    def all_operating_countries(self) -> IntentResult:
        """Return full list of countries for the operating-country dropdown."""
        return IntentResult(was_intent_successful=True, data=all_operating_countries())

    def has_tax_model(self, country: str) -> IntentResult:
        """Check whether a country has a tax data package."""
        return IntentResult(was_intent_successful=True, data=has_tax_model(country))

    @fails_with("Failed to compute monthly VAT", append_exception=True)
    def get_monthly_vat(self, year: int | None = None) -> IntentResult:
        """Get monthly VAT breakdown."""
        invoices = self.query(Invoice)
        country = self._get_country()
        currency = self._get_tax_currency(country)
        left_out: list = []
        months = monthly_vat_breakdown(invoices, year=year, currency=currency, left_out=left_out)
        data = {"months": months, "currency": currency, "unconverted": distinct(left_out)}
        return IntentResult(was_intent_successful=True, data=data)
