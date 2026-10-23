"""Without a tax model there is no after-tax figure: no tax of zero passed off as an estimate."""

import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.tax.intent import TaxIntent
from tuttle.app_db import AppDatabase
from tuttle.forecasting import cash_flow_series
from tuttle.kpi import compute_kpis, monthly_spendable_breakdown
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project, RecurringExpense
from tuttle.tax import NoTaxRules
from tuttle.tax_reserves import compute_effective_salary, compute_income_tax_reserve, compute_spendable_income
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()
LAST_MONTH = TODAY.replace(day=1) - datetime.timedelta(days=1)


@pytest.fixture(autouse=True)
def euro_aggregates():
    """Keep every figure in EUR, whatever the country's own currency."""
    AppDatabase().set_setting("currency.primary", "EUR")


def _invoice(date: datetime.date, net: str, paid: bool = True) -> Invoice:
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="0150", city="Oslo", country="Norway"),
    )
    contract = Contract(
        title="Heating",
        client=client,
        rate=Decimal("100"),
        currency="EUR",
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    project = Project(title="Boiler", tag="#boiler", start_date=date, contract=contract)
    inv = Invoice(number=f"{date}-1", date=date, contract=contract, project=project, sent=True, paid=paid)
    InvoiceItem(invoice=inv, quantity=1, unit="flat", unit_price=Decimal(net), VAT_rate=Decimal("0.25"), description="Work")
    return inv


def _expenses() -> list:
    return [
        RecurringExpense(title="Rent", amount=Decimal("1000"), period=Cycle.monthly, tax_deductible=True),
        RecurringExpense(title="Health", amount=Decimal(0), period=Cycle.monthly, rate=Decimal("10"), tax_deductible=True),
        RecurringExpense(title="Savings", amount=Decimal(0), period=Cycle.monthly, rate=Decimal("10"), tax_deductible=False),
    ]


def test_the_reason_names_what_is_missing():
    with pytest.raises(NoTaxRules, match=r"^No tax model for Norway\.$"):
        compute_income_tax_reserve(Decimal(50000), "Norway")
    with pytest.raises(NoTaxRules, match=r"^No operating country set\.$"):
        compute_income_tax_reserve(Decimal(0), "")


def test_tax_view_keeps_pre_tax_figures_and_shows_nothing_after_tax():
    spending = compute_spendable_income(
        [_invoice(TODAY.replace(day=1), "5000")], "Norway", expenses=_expenses(), currency="EUR"
    )

    assert spending.net_revenue_ytd == 5000
    assert spending.vat_reserve == 1250
    assert spending.business_expenses == 12000
    assert spending.tax_base == spending.taxable_profit - spending.dynamic_expenses_deductible
    assert spending.income_tax_reserve is None
    assert spending.dynamic_expenses_post_tax is None
    assert spending.spendable is None
    assert spending.tax_unavailable_reason == "No tax model for Norway."
    lines = {line.title: line.amount for line in spending.dynamic_expenses}
    assert lines["Health"] is not None
    assert lines["Savings"] is None


def test_a_country_with_a_tax_model_still_gets_an_estimate():
    spending = compute_spendable_income([_invoice(TODAY.replace(day=1), "50000")], "Germany", currency="EUR")
    assert spending.income_tax_reserve > 0
    assert spending.spendable is not None
    assert spending.tax_unavailable_reason is None


def test_dashboard_shows_no_spendable_income():
    kpis = compute_kpis([_invoice(TODAY.replace(day=1), "5000")], [], [], country="Norway")

    assert kpis.total_revenue_ytd == 5000
    assert kpis.income_tax_reserve is None
    assert kpis.spendable_income is None
    assert not kpis.country_supported
    assert kpis.tax_unavailable_reason == "No tax model for Norway."
    rpc = kpis.to_rpc_dict()
    assert rpc["spendable_income_formatted"] == "—"
    assert rpc["income_tax_reserve_formatted"] == "—"


def test_salary_shows_no_salary_but_keeps_what_does_not_depend_on_tax():
    salary = compute_effective_salary([_invoice(LAST_MONTH, "5000")], _expenses(), "Norway", currency="EUR")

    assert salary.conservative_monthly is None
    assert salary.optimistic_monthly is None
    assert salary.income_tax_reserve_monthly is None
    assert salary.tax_unavailable_reason == "No tax model for Norway."
    assert salary.gross_monthly == 6250
    assert salary.vat_reserve_monthly == 1250
    assert salary.monthly_expenses == 1000
    lines = {line.title: line.amount for line in salary.dynamic_expenses}
    assert lines["Health"] == 400
    assert lines["Savings"] is None


def test_cash_flow_reserves_no_tax_and_says_so():
    overdue = _invoice(TODAY - datetime.timedelta(days=60), "5000", paid=False)
    cash = cash_flow_series([overdue], [], [], _expenses(), None, forecast_months=3, country="Norway", today=TODAY)

    assert cash["tax_included"] is False
    assert cash["tax_unavailable_reason"] == "No tax model for Norway."
    assert cash["left_out_with_tax"] == ["Savings"]
    this_month, next_month = cash["buckets"][0], cash["buckets"][1]
    assert this_month["inflow_invoiced"] == 5000
    # Rent and the deductible 10% on the 4,000 left after it; no tax, no savings.
    assert this_month["outflow"] == 1400
    assert next_month["outflow"] == 1000


def test_cash_flow_with_a_tax_model_includes_tax():
    overdue = _invoice(TODAY - datetime.timedelta(days=60), "5000", paid=False)
    cash = cash_flow_series([overdue], [], [], _expenses(), None, forecast_months=3, country="Germany", today=TODAY)

    assert cash["tax_included"] is True
    assert cash["tax_unavailable_reason"] is None
    assert cash["left_out_with_tax"] == []


def test_monthly_breakdown_shows_no_spendable_figure_this_year():
    months = monthly_spendable_breakdown([_invoice(TODAY.replace(day=1), "5000")], country="Norway", n_months=3)
    this_month = next(m for m in months if m["month"] == f"{TODAY:%Y-%m}")
    assert this_month["net_revenue"] == 5000
    assert this_month["income_tax_true_up"] is None
    assert this_month["spendable"] is None


def test_tax_view_estimate_has_no_tax_reserve(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    intent = TaxIntent()
    intent._time_data_source = SimpleNamespace(get_data_frame=lambda: None)
    monkeypatch.setattr(intent, "_get_country", lambda: "Norway")

    result = intent.get_income_tax_estimate()

    assert result.was_intent_successful
    assert result.data["tax_reserve"] is None
    assert result.data["brackets"] == []
    assert result.data["country_supported"] is False
    assert result.data["tax_unavailable_reason"] == "No tax model for Norway."
