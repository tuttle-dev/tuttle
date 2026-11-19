"""The dashboard's Spendable Income is the tax view's Safe to Spend, Contracted revenue included."""

import datetime
from decimal import Decimal

import pytest

from tuttle.app.tax.intent import TaxIntent
from tuttle.kpi import compute_kpis
from tuttle.model import Address, Client, Contract, Project, RecurringExpense
from tuttle.tax_reserves import compute_spendable_income
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()


@pytest.fixture
def project():
    """An agreed contract with 200 h left at 100, running into next year."""
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
        title="Heating",
        client=client,
        start_date=TODAY - datetime.timedelta(days=30),
        end_date=datetime.date(TODAY.year + 1, 6, 30),
        rate=Decimal("100.00"),
        currency="EUR",
        unit=TimeUnit.hour,
        units_per_workday=8,
        volume=200,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    return Project(
        title="Boiler",
        tag="#boiler",
        description="",
        start_date=contract.start_date,
        end_date=contract.end_date,
        contract=contract,
    )


def test_dashboard_spendable_income_equals_the_tax_views(project):
    expenses = [RecurringExpense(title="Rent", amount=Decimal("500"), period=Cycle.monthly, tax_deductible=True)]
    contracted = TaxIntent.__new__(TaxIntent)._contracted_this_year(None, [], [project], None, "EUR")
    tax_view = compute_spendable_income(
        [], "Germany", expenses=expenses, currency="EUR", projects=[project], contracted=contracted
    )

    kpis = compute_kpis([], [project.contract], [project], country="Germany", expenses=expenses)

    assert contracted > 0
    assert kpis.spendable_income == tax_view.spendable
    assert kpis.income_tax_reserve == tax_view.income_tax_reserve
