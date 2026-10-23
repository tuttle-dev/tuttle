"""Totals leave out amounts without an exchange rate, and say which."""

import datetime
import urllib.error
from decimal import Decimal
from types import SimpleNamespace

import pandas
import pytest

from tuttle import fx
from tuttle.app.dashboard.intent import DashboardIntent
from tuttle.forecasting import cash_flow_series, contracted_this_year, revenue_series
from tuttle.kpi import compute_kpis
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project, RecurringExpense
from tuttle.tax import TaxUnavailable
from tuttle.tax_reserves import (
    compute_effective_salary,
    compute_income_tax_reserve,
    compute_planned_revenue,
    compute_spendable_income,
    monthly_vat_breakdown,
)
from tuttle.time import Cycle, TimeUnit

from .conftest import STUB_FX_RATE

TODAY = datetime.date.today()
THIS_MONTH = TODAY.replace(day=1)
LAST_MONTH = THIS_MONTH - datetime.timedelta(days=1)


@pytest.fixture
def offline(monkeypatch):
    """No rate can be fetched for the months passed; every other month has one."""

    def cut(*months: datetime.date):
        keys = {f"{m:%Y-%m}" for m in months}

        def fetch(base, quote, month):
            if f"{month:%Y-%m}" in keys:
                raise urllib.error.URLError("offline")
            return STUB_FX_RATE

        monkeypatch.setattr(fx, "_fetch_monthly_average", fetch)

    return cut


def _project(currency: str = "EUR") -> Project:
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
        title="Heating",
        client=client,
        start_date=TODAY - datetime.timedelta(days=30),
        end_date=datetime.date(TODAY.year + 1, 6, 30),
        rate=Decimal("100"),
        currency=currency,
        unit=TimeUnit.hour,
        units_per_workday=8,
        volume=200,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    return Project(
        title="Boiler", tag="#boiler", start_date=contract.start_date, end_date=contract.end_date, contract=contract
    )


def _invoice(date: datetime.date, net: str, currency: str = "EUR", paid: bool = True) -> Invoice:
    project = _project(currency)
    inv = Invoice(number=f"{date}-{currency}", date=date, contract=project.contract, project=project, sent=True, paid=paid)
    InvoiceItem(invoice=inv, quantity=1, unit="flat", unit_price=Decimal(net), VAT_rate=Decimal("0"), description="Work")
    return inv


def _usd_label(date: datetime.date) -> str:
    return f"Invoice {date}-USD (USD, {date:%b %Y})"


def _software() -> RecurringExpense:
    return RecurringExpense(title="Software", amount=Decimal("100"), currency="USD", period=Cycle.monthly, tax_deductible=True)


def test_tax_view_leaves_out_an_invoice_and_names_it(offline):
    offline(THIS_MONTH)
    invoices = [_invoice(THIS_MONTH, "1000"), _invoice(THIS_MONTH, "2000", currency="USD")]

    spending = compute_spendable_income(invoices, "Germany", currency="EUR")

    assert spending.net_revenue_ytd == 1000
    assert spending.unconverted == [_usd_label(THIS_MONTH)]


def test_tax_view_leaves_out_an_expense_and_names_it(offline):
    offline(THIS_MONTH)
    spending = compute_spendable_income([], "Germany", expenses=[_software()], currency="EUR")

    assert spending.business_expenses == 0
    assert spending.unconverted == ["Expense Software (USD)"]


def test_monthly_vat_names_what_it_leaves_out(offline):
    offline(THIS_MONTH)
    left_out = []
    monthly_vat_breakdown([_invoice(THIS_MONTH, "2000", currency="USD")], currency="EUR", left_out=left_out)
    assert left_out == [_usd_label(THIS_MONTH)]


def test_planned_work_without_a_rate_is_named(offline):
    offline(THIS_MONTH)
    project = _project("USD")
    begin = datetime.datetime(TODAY.year, TODAY.month, 1, 9)
    work = pandas.DataFrame(
        {
            "begin": [begin],
            "end": [begin + datetime.timedelta(hours=8)],
            "title": ["Work"],
            "tag": [project.tag],
            "description": [""],
            "all_day": [False],
        }
    )
    work["duration"] = work["end"] - work["begin"]
    left_out = []

    planned = compute_planned_revenue([project], work.set_index("begin"), currency="EUR", left_out=left_out)

    assert planned == 0
    assert left_out == ["Planned work on Boiler (USD)"]


def test_contracted_work_without_a_rate_is_named(offline):
    offline(THIS_MONTH)
    left_out = []
    contracted = contracted_this_year([_project("USD")], [], None, currency="EUR", left_out=left_out)
    assert contracted == 0
    assert left_out == ["Contracted work on Heating (USD)"]


def test_dashboard_kpis_name_each_left_out_amount_once(offline):
    offline(THIS_MONTH)
    invoices = [_invoice(THIS_MONTH, "1000"), _invoice(THIS_MONTH, "2000", currency="USD")]

    kpis = compute_kpis(invoices, [], [], country="Germany", expenses=[_software()])

    assert kpis.total_revenue_ytd == 1000
    # The revenue loop and Spendable Income both meet the invoice; it is named once.
    assert kpis.unconverted == [_usd_label(THIS_MONTH), "Expense Software (USD)"]


def test_revenue_chart_names_what_it_leaves_out(offline):
    offline(THIS_MONTH)
    series = revenue_series([_invoice(THIS_MONTH, "2000", currency="USD")], [], None, today=TODAY)
    assert series["total"] == 0
    assert series["unconverted"] == [_usd_label(THIS_MONTH)]


def test_cash_flow_names_what_it_leaves_out(offline):
    offline(THIS_MONTH)
    unpaid = _invoice(THIS_MONTH, "2000", currency="USD", paid=False)
    cash = cash_flow_series([unpaid], [], [], [_software()], None, forecast_months=3, country="Germany", today=TODAY)

    assert cash["total_inflow"] == 0
    assert cash["unconverted"] == [_usd_label(THIS_MONTH), "Expense Software (USD)"]


def test_salary_names_what_it_leaves_out(offline):
    offline(LAST_MONTH)
    invoices = [_invoice(LAST_MONTH, "1000"), _invoice(LAST_MONTH, "2000", currency="USD")]

    salary = compute_effective_salary(invoices, [], "Germany", currency="EUR")

    assert salary.gross_monthly == 1000
    assert salary.unconverted == [_usd_label(LAST_MONTH)]


def test_goals_name_what_their_year_leaves_out(offline):
    offline(THIS_MONTH)
    invoices = [_invoice(THIS_MONTH, "1000"), _invoice(THIS_MONTH, "2000", currency="USD")]

    totals, left_out = DashboardIntent.__new__(DashboardIntent)._revenue_by_target_year(invoices, "EUR")

    assert totals == {TODAY.year: Decimal("1000")}
    assert left_out[TODAY.year] == [_usd_label(THIS_MONTH)]


def test_no_tax_estimate_without_a_rate_into_the_tax_currency(offline):
    """Income in dollars is not taxed as if a dollar were a euro."""
    offline(datetime.date(2025, 7, 1))
    with pytest.raises(TaxUnavailable, match=r"^No USD/EUR exchange rate for Jul 2025\.$"):
        compute_income_tax_reserve(Decimal(50000), "Germany", year=2025, currency="USD")

    income = [_invoice(datetime.date(2025, 3, 1), "50000", currency="USD")]
    spending = compute_spendable_income(income, "Germany", currency="USD", year=2025)
    assert spending.net_revenue_ytd == 50000
    assert spending.income_tax_reserve is None
    assert spending.tax_unavailable_reason == "No USD/EUR exchange rate for Jul 2025."


def test_a_failed_lookup_is_tried_again(offline, monkeypatch):
    """Back online, the rate is found: an offline moment does not last the session."""
    clock = [1000.0]
    monkeypatch.setattr(fx, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    offline(THIS_MONTH)
    assert fx.rate("USD", "EUR", THIS_MONTH) is None

    offline()
    clock[0] += fx._RETRY_AFTER
    assert fx.rate("USD", "EUR", THIS_MONTH) == STUB_FX_RATE
    spending = compute_spendable_income([_invoice(THIS_MONTH, "2000", currency="USD")], "Germany", currency="EUR")
    assert spending.net_revenue_ytd == 1800
    assert spending.unconverted == []


def test_a_failed_lookup_is_not_repeated_for_every_amount(offline, monkeypatch):
    """Within a minute of a failure the network is not asked again, so a page does not wait on it per amount."""
    calls = []
    offline(THIS_MONTH)
    failing = fx._fetch_monthly_average
    monkeypatch.setattr(fx, "_fetch_monthly_average", lambda *args: calls.append(args) or failing(*args))

    invoices = [_invoice(THIS_MONTH, "1000", currency="USD"), _invoice(THIS_MONTH, "2000", currency="USD")]
    compute_spendable_income(invoices, "Germany", currency="EUR")

    assert len(calls) == 1
