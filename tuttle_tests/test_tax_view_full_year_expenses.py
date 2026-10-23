"""The tax estimate counts the year's expenses for the same months as its income: all twelve."""

import datetime
from decimal import Decimal

import pandas
import pytest

from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project, RecurringExpense, Timesheet
from tuttle.tax_reserves import compute_spendable_income
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()
DECEMBER = datetime.date(TODAY.year, 12, 1)


@pytest.fixture
def project():
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
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


def _invoice(project, date: datetime.date, net: str, work_day: datetime.date = None) -> Invoice:
    inv = Invoice(number="2026-001", date=date, contract=project.contract, project=project, sent=True)
    InvoiceItem(invoice=inv, quantity=1, unit="flat", unit_price=Decimal(net), VAT_rate=Decimal("0.19"), description="Work")
    if work_day:
        Timesheet(title="ts", date=date, period_start=work_day, period_end=work_day, project=project, invoice=inv)
    return inv


def _rent(amount="1000"):
    return RecurringExpense(title="Rent", amount=Decimal(amount), period=Cycle.monthly, tax_deductible=True)


def test_december_work_is_taxed_with_december_rent_deducted(project):
    spending = compute_spendable_income(
        [], "Germany", expenses=[_rent()], currency="EUR", projects=[project], time_data=_work(project.tag, DECEMBER)
    )
    assert spending.planned_revenue == 4000
    assert spending.business_expenses == 12000
    assert spending.taxable_profit == 4000 - 12000


def test_an_invoice_dated_later_this_year_still_counts(project):
    """Its timesheet takes the work out of Planned, so the invoice must count instead."""
    later = _invoice(project, datetime.date(TODAY.year, 12, 31), "4000", work_day=DECEMBER)
    spending = compute_spendable_income(
        [later], "Germany", currency="EUR", projects=[project], time_data=_work(project.tag, DECEMBER)
    )
    assert spending.planned_revenue == 0
    assert spending.net_revenue_ytd == 4000


def test_dynamic_expenses_are_charged_every_month_on_the_average_month_invoiced(project):
    health = RecurringExpense(title="Health", amount=Decimal(0), rate=Decimal("10"), period=Cycle.monthly, tax_deductible=True)
    january = _invoice(project, datetime.date(TODAY.year, 1, 1), "12000")
    spending = compute_spendable_income([january], "Germany", expenses=[health], currency="EUR")

    monthly = (Decimal(12000) / TODAY.month * Decimal("0.10")).quantize(Decimal("0.01"))
    assert spending.dynamic_expenses_deductible == monthly * 12


def test_a_past_year_counts_its_twelve_months(project):
    year = TODAY.year - 1
    invoice = _invoice(project, datetime.date(year, 6, 1), "24000")
    invoice.paid = True
    spending = compute_spendable_income([invoice], "Germany", expenses=[_rent()], currency="EUR", year=year)
    assert spending.business_expenses == 12000
    assert spending.taxable_profit == 24000 - 12000
