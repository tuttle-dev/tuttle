"""The dashboard's overview of the year: where the income comes from, where it goes, and what is ready to invoice."""

import datetime
from decimal import Decimal

import pandas
import pytest

from tuttle.kpi import compute_kpis
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project, RecurringExpense, Timesheet
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)
TOMORROW = TODAY + datetime.timedelta(days=1)

# Tracked work needs a day before today in this year, scheduled work one after it.
needs_both_sides_of_today = pytest.mark.skipif(
    YESTERDAY.year != TODAY.year or TOMORROW.year != TODAY.year, reason="today is the first or last day of the year"
)


@pytest.fixture
def project():
    """An agreed contract for 200 h at 100, running into next year."""
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
        VAT_rate=Decimal("0.19"),
        title="Heating",
        client=client,
        start_date=datetime.date(TODAY.year, 1, 1),
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


def _work(tag: str, *days: datetime.date) -> pandas.DataFrame:
    """8 h of work on each of *days*."""
    begins = [datetime.datetime(d.year, d.month, d.day, 9) for d in days]
    df = pandas.DataFrame(
        {
            "begin": begins,
            "end": [b + datetime.timedelta(hours=8) for b in begins],
            "title": ["Work"] * len(days),
            "tag": [tag] * len(days),
            "description": [""] * len(days),
            "all_day": [False] * len(days),
        }
    )
    df["duration"] = df["end"] - df["begin"]
    return df.set_index("begin")


def _invoice(project, *, work_day: datetime.date = None, **flags) -> Invoice:
    """An invoice of today for 8 h at 100 + 19% VAT, with a timesheet covering *work_day* if given."""
    inv = Invoice(number="2026-001", date=TODAY, contract=project.contract, project=project, **flags)
    InvoiceItem(
        invoice=inv, quantity=8, unit="hour", unit_price=Decimal("100.00"), VAT_rate=Decimal("0.19"), description="Work"
    )
    if work_day:
        Timesheet(title="ts", date=TODAY, period_start=work_day, period_end=work_day, project=project, invoice=inv)
    return inv


def _expenses() -> list:
    return [
        RecurringExpense(title="Rent", amount=Decimal("500"), period=Cycle.monthly, tax_deductible=True),
        RecurringExpense(title="Gym", amount=Decimal("50"), period=Cycle.monthly, tax_deductible=False),
        RecurringExpense(
            title="Health Insurance",
            amount=Decimal(0),
            currency="EUR",
            period=Cycle.monthly,
            category="health",
            rate=Decimal("19.6"),
            tax_deductible=True,
        ),
    ]


@needs_both_sides_of_today
def test_the_years_income_less_tax_and_expenses_is_spendable_income(project):
    invoices = [_invoice(project, paid=True), _invoice(project, sent=True)]
    kpis = compute_kpis(
        invoices,
        [project.contract],
        [project],
        country="Germany",
        time_data=_work(project.tag, YESTERDAY, TOMORROW),
        expenses=_expenses(),
    )

    income = kpis.received_net + kpis.invoiced_net + kpis.planned_revenue + kpis.contracted_revenue
    assert (kpis.received_net, kpis.invoiced_net, kpis.planned_revenue) == (800, 800, 1600)
    assert kpis.contracted_revenue > 0
    assert kpis.expenses > 0
    assert income - kpis.income_tax_reserve - kpis.expenses == kpis.spendable_income


@needs_both_sides_of_today
def test_ready_to_invoice_is_tracked_work_without_an_invoice(project):
    work = _work(project.tag, YESTERDAY, TOMORROW)
    kpis = compute_kpis([], [project.contract], [project], country="Germany", time_data=work)
    assert kpis.ready_to_invoice == 800  # yesterday's work; tomorrow's is only scheduled
    assert kpis.planned_revenue == 1600

    invoiced = [_invoice(project, work_day=YESTERDAY, sent=True)]
    kpis = compute_kpis(invoiced, [project.contract], [project], country="Germany", time_data=work)
    assert kpis.ready_to_invoice == 0


@needs_both_sides_of_today
def test_work_on_a_draft_is_still_ready_to_invoice(project):
    draft = [_invoice(project, work_day=YESTERDAY)]
    kpis = compute_kpis(draft, [project.contract], [project], country="Germany", time_data=_work(project.tag, YESTERDAY))
    assert kpis.ready_to_invoice == 800


def test_without_tax_rules_the_expenses_are_unknown(project):
    kpis = compute_kpis([_invoice(project, paid=True)], [], [project], country="Norway", expenses=_expenses())
    assert kpis.received_net > 0  # in kroner
    assert kpis.expenses is kpis.income_tax_reserve is kpis.spendable_income is None
