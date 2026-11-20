"""The tax view can leave out the forecasts, Planned and Contracted, to show the year from invoices alone."""

import datetime
from decimal import Decimal
from types import SimpleNamespace

import pandas
import pytest
from sqlmodel import Session, SQLModel, create_engine

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.tax.intent import TaxIntent
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()
CONTRACTED = Decimal("5000")


def _work(tag: str, day: datetime.date) -> pandas.DataFrame:
    """40 h of work, worth 4,000 at 100 an hour."""
    begin = datetime.datetime(day.year, day.month, day.day, 9)
    df = pandas.DataFrame(
        {
            "begin": [begin],
            "end": [begin + datetime.timedelta(hours=40)],
            "title": ["Work"],
            "tag": [tag],
            "description": [""],
            "all_day": [False],
        }
    )
    df["duration"] = df["end"] - df["begin"]
    return df.set_index("begin")


@pytest.fixture
def intent(monkeypatch):
    """A tax view over one paid invoice, 4,000 of planned work and 5,000 of contracted work."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
        title="Heating",
        client=client,
        start_date=datetime.date(TODAY.year, 1, 1),
        rate=Decimal("100"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    project = Project(title="Boiler", tag="#boiler", description="", start_date=contract.start_date, contract=contract)
    invoice = Invoice(
        number="1", date=datetime.date(TODAY.year, 1, 15), contract=contract, project=project, sent=True, paid=True
    )
    InvoiceItem(
        invoice=invoice, quantity=1, unit="flat", unit_price=Decimal("60000"), VAT_rate=Decimal("0.19"), description="Work"
    )
    with Session(engine) as session:
        session.add(invoice)
        session.commit()

    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    intent = TaxIntent()
    work_day = datetime.date(TODAY.year, 12, 1)
    intent._time_data_source = SimpleNamespace(get_data_frame=lambda: _work("#boiler", work_day))
    monkeypatch.setattr(intent, "_get_country", lambda: "Germany")
    monkeypatch.setattr(intent, "_get_tax_currency", lambda country: "EUR")
    monkeypatch.setattr(intent, "_contracted_this_year", lambda *args, **kwargs: CONTRACTED)
    return intent


def _spending(intent, **params):
    result = intent.get_spendable_income(**params)
    assert result.was_intent_successful
    return result.data["spending"]


def test_both_forecasts_count_by_default(intent):
    spending = _spending(intent)
    assert spending.planned_revenue == 4000
    assert spending.contracted_revenue == CONTRACTED
    assert spending.taxable_profit == 60000 + 4000 + CONTRACTED


def test_without_planned_work(intent):
    spending = _spending(intent, include_planned=False)
    assert spending.planned_revenue == 0
    assert spending.contracted_revenue == CONTRACTED
    assert spending.taxable_profit == 60000 + CONTRACTED


def test_without_contracted_work(intent):
    spending = _spending(intent, include_contracted=False)
    assert spending.planned_revenue == 4000
    assert spending.contracted_revenue == 0
    assert spending.taxable_profit == 60000 + 4000


def test_from_invoices_alone_the_tax_is_lower(intent):
    both = _spending(intent)
    invoiced = _spending(intent, include_planned=False, include_contracted=False)
    assert invoiced.taxable_profit == 60000
    assert invoiced.income_tax_reserve < both.income_tax_reserve
    # The invoices themselves are untouched.
    assert invoiced.received_gross == both.received_gross
    assert invoiced.vat_reserve == both.vat_reserve


def test_the_income_tax_estimate_leaves_out_the_same_forecasts(intent):
    spending = _spending(intent, include_planned=False, include_contracted=False)
    estimate = intent.get_income_tax_estimate(include_planned=False, include_contracted=False).data
    assert estimate["income_basis"] == spending.tax_base
    assert estimate["planned_revenue"] == 0
    assert estimate["contracted_revenue"] == 0
    assert estimate["tax_reserve"].total_annual_reserve == spending.income_tax_reserve
