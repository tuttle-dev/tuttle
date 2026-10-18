"""A year without its own tax data is estimated with the nearest year's rules,
and the income tax estimate says which year that is."""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.tax.intent import TaxIntent
from tuttle.app.timetracking.data_source import TimeTrackingDataFrameSource
from tuttle.model import Contract, Invoice, InvoiceItem, User
from tuttle.tax import available_years, get_tax_system

GERMAN_YEARS = available_years("Germany")


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    # The time-tracking frame is a singleton and may still hold another test's rows.
    monkeypatch.setattr(TimeTrackingDataFrameSource(), "get_data_frame", lambda: None)
    return engine


def _freelancer(engine, country: str, year: int) -> None:
    """A user working in *country* with €60,000 net invoiced in *year*."""
    day = datetime.date(year, 1, 1)
    with Session(engine) as session:
        session.add(User(name="Harry Tuttle", subtitle="Heating Engineer", email="mail@tuttle.com", operating_country=country))
        contract = Contract(title="Duct Repairs", start_date=day, rate=Decimal(100), currency="EUR", VAT_rate=Decimal("0.19"))
        item = InvoiceItem(
            start_date=day,
            end_date=day,
            quantity=600,
            unit="hour",
            unit_price=Decimal(100),
            VAT_rate=Decimal("0.19"),
            description="Duct repairs",
        )
        session.add(Invoice(number=f"{year}-001", date=day, contract=contract, sent=True, paid=True, items=[item]))
        session.commit()


def _estimate(year: int) -> dict:
    result = TaxIntent().get_income_tax_estimate(year=year)
    assert result.was_intent_successful, result.error_msg
    return result.data


@pytest.mark.parametrize(
    "year, rules_year",
    [
        (GERMAN_YEARS[0] - 1, GERMAN_YEARS[0]),  # before the data: the earliest rules
        (GERMAN_YEARS[-1] + 1, GERMAN_YEARS[-1]),  # after the data: the latest rules
        (GERMAN_YEARS[-1], GERMAN_YEARS[-1]),  # a year with data: its own rules
    ],
)
def test_the_estimate_names_the_year_whose_rules_it_uses(in_memory_db, year, rules_year):
    _freelancer(in_memory_db, "Germany", year)

    data = _estimate(year)

    assert data["rules_year"] == rules_year
    rules = get_tax_system("Germany", date=datetime.date(rules_year, 7, 1))
    assert data["income_basis"] == Decimal(60000)
    assert data["tax_reserve"].estimated_annual_tax == rules.income_tax(data["income_basis"])
    assert data["brackets"][0]["end"] == rules.params.basic_allowance


def test_no_rules_year_without_a_tax_model(in_memory_db):
    _freelancer(in_memory_db, "Norway", GERMAN_YEARS[-1])

    data = _estimate(GERMAN_YEARS[-1])

    assert data["country_supported"] is False
    assert data["rules_year"] is None
