"""Business logic for the Tax view."""

import datetime
from decimal import Decimal

from ..core.abstractions import SQLModelDataSourceMixin, Intent
from ..core.intent_result import IntentResult
from ..timetracking.data_source import TimeTrackingDataFrameSource

from ...model import Invoice, Project, RecurringExpense, User
from ...tax import get_tax_system, supported_countries
from ...tax_reserves import (
    compute_spendable_income,
    compute_income_tax_reserve,
    monthly_vat_breakdown,
)


class TaxIntent(SQLModelDataSourceMixin, Intent):
    """Gathers tax-related data for the freelance tax planning view."""

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

    def _get_tax_currency(self, country: str) -> str:
        """Return the ISO 4217 currency for the country's tax system."""
        try:
            return get_tax_system(country).currency
        except NotImplementedError:
            return "EUR"

    def get_spendable_income(self, year: int | None = None) -> IntentResult:
        """Compute spendable income breakdown."""
        try:
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
            )
            data = {"spending": spending, "currency": currency}
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to compute spendable income: {e}",
                log_message=f"TaxIntent.get_spendable_income: {e}",
                exception=e,
            )

    def get_income_tax_estimate(self, year: int | None = None) -> IntentResult:
        """Get detailed income tax estimate with bracket info."""
        try:
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
            )

            total_income = spending.taxable_profit
            tax_reserve = compute_income_tax_reserve(total_income, country, year=year)

            ref_date = datetime.date(year, 7, 1) if year else today
            try:
                tax_system = get_tax_system(country, date=ref_date)
                bracket_data = self._compute_bracket_data(tax_system, total_income)
                country_supported = True
            except NotImplementedError:
                bracket_data = []
                country_supported = False

            data = {
                "tax_reserve": tax_reserve,
                "income_basis": total_income,
                "received_net": spending.received_net,
                "outstanding_net": spending.outstanding_net,
                "planned_revenue": spending.planned_revenue,
                "brackets": bracket_data,
                "country": country,
                "country_supported": country_supported,
                "currency": currency,
            }
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to compute income tax estimate: {e}",
                log_message=f"TaxIntent.get_income_tax_estimate: {e}",
                exception=e,
            )

    def _compute_bracket_data(self, tax_system, income: Decimal) -> list:
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
            elif ztype in ("quadratic", "linear") and "reference_offset" in zone:
                # German-style zones with explicit reference offsets
                start = zone["reference_offset"]
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
                    "is_current": start
                    <= income_f
                    < (end if up_to is not None else float("inf")),
                }
            )
            prev_end = end
        return brackets

    def get_available_years(self) -> IntentResult:
        """Return distinct years (descending) that have invoice data."""
        try:
            invoices = self.query(Invoice)
            years = sorted(
                {inv.date.year for inv in invoices if not inv.cancelled},
                reverse=True,
            )
            return IntentResult(was_intent_successful=True, data=years)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to get available years: {e}",
                log_message=f"TaxIntent.get_available_years: {e}",
                exception=e,
            )

    def supported_countries(self) -> IntentResult:
        """Return list of countries with tax system support."""
        return IntentResult(was_intent_successful=True, data=supported_countries())

    def get_monthly_vat(self, year: int | None = None) -> IntentResult:
        """Get monthly VAT breakdown."""
        try:
            invoices = self.query(Invoice)
            country = self._get_country()
            currency = self._get_tax_currency(country)
            months = monthly_vat_breakdown(invoices, year=year, currency=currency)
            data = {"months": months, "currency": currency}
            return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to compute monthly VAT: {e}",
                log_message=f"TaxIntent.get_monthly_vat: {e}",
                exception=e,
            )
