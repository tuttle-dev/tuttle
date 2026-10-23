"""The cash flow reserves income tax at the tax view's effective rate for the year."""

import datetime
from decimal import Decimal

import pandas
import pytest

from tuttle.forecasting import cash_flow_series, contracted_this_year
from tuttle.model import Address, Client, Contract, Project, RecurringExpense
from tuttle.tax_reserves import compute_spendable_income
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()


@pytest.fixture
def project():
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
        id=1,
        title="Heating",
        client=client,
        start_date=datetime.date(TODAY.year, 1, 1),
        rate=Decimal("100.00"),
        currency="EUR",
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    return Project(title="Boiler", tag="#boiler", description="", start_date=contract.start_date, contract=contract)


def _backlog(tag: str) -> pandas.DataFrame:
    """300 h tracked at the start of the year and never invoiced: 30,000 that arrive this month."""
    begin = datetime.datetime(TODAY.year, 1, 1, 9)
    df = pandas.DataFrame(
        {
            "begin": [begin],
            "end": [begin + datetime.timedelta(hours=300)],
            "title": ["Work"],
            "tag": [tag],
            "description": [""],
            "all_day": [False],
        }
    )
    df["duration"] = df["end"] - df["begin"]
    return df.set_index("begin")


def _tax_view_rate(invoices, projects, time_data, expenses=()) -> Decimal:
    spending = compute_spendable_income(
        invoices,
        "Germany",
        expenses=list(expenses),
        currency="EUR",
        year=TODAY.year,
        projects=projects,
        time_data=time_data,
        contracted=contracted_this_year(projects, invoices, time_data, currency="EUR"),
    )
    return spending.income_tax_reserve / spending.tax_base


def test_a_backlog_arriving_at_once_is_taxed_at_the_years_rate(project):
    backlog = _backlog(project.tag)
    cash = cash_flow_series([], [project.contract], [project], [], backlog, country="Germany", today=TODAY)

    this_month = cash["buckets"][0]
    assert this_month["inflow_planned"] == 30000
    rate = _tax_view_rate([], [project], backlog)
    assert this_month["outflow"] == float((Decimal(30000) * rate).quantize(Decimal("0.01")))


def test_deductible_expenses_lower_the_tax_base_but_not_the_rate(project):
    rent = RecurringExpense(title="Rent", amount=Decimal("1000"), period=Cycle.monthly, tax_deductible=True)
    backlog = _backlog(project.tag)
    cash = cash_flow_series([], [project.contract], [project], [rent], backlog, country="Germany", today=TODAY)

    rate = _tax_view_rate([], [project], backlog, [rent])
    tax = (Decimal(30000 - 1000) * rate).quantize(Decimal("0.01"))
    assert cash["buckets"][0]["outflow"] == float(Decimal(1000) + tax)
