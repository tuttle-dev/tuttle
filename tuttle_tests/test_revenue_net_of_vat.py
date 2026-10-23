"""Revenue is net of VAT everywhere; only what clients owe includes it."""

import datetime
from decimal import Decimal

import pandas
import pytest

from tuttle.app.dashboard.intent import DashboardIntent
from tuttle.forecasting import revenue_series
from tuttle.kpi import compute_kpis
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project, Timesheet
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()


@pytest.fixture
def project():
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
        title="Heating",
        client=client,
        start_date=datetime.date(TODAY.year - 1, 1, 1),
        rate=Decimal("100.00"),
        currency="EUR",
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    return Project(title="Boiler", tag="#boiler", description="", start_date=contract.start_date, contract=contract)


def _work(tag: str, day: datetime.date, hours: int = 40) -> pandas.DataFrame:
    begin = datetime.datetime(day.year, day.month, day.day, 9)
    df = pandas.DataFrame(
        {
            "begin": [begin],
            "end": [begin + datetime.timedelta(hours=hours)],
            "title": ["Work"],
            "tag": [tag],
            "description": [""],
            "all_day": [False],
        }
    )
    df["duration"] = df["end"] - df["begin"]
    return df.set_index("begin")


def _invoice(project, date, work_day=None, **flags) -> Invoice:
    """40 h at 100 = 4,000 net, 4,760 with 19% VAT."""
    inv = Invoice(number="2026-001", date=date, contract=project.contract, project=project, **flags)
    InvoiceItem(
        invoice=inv, quantity=40, unit="hour", unit_price=Decimal("100.00"), VAT_rate=Decimal("0.19"), description="Work"
    )
    if work_day:
        Timesheet(title="ts", date=date, period_start=work_day, period_end=work_day, project=project, invoice=inv)
    return inv


@pytest.mark.parametrize("flags", [{"sent": True}, {"sent": True, "paid": True}])
def test_invoicing_planned_work_keeps_the_chart_total(project, flags):
    work = _work(project.tag, TODAY)
    before = revenue_series([], [project], work, "month", today=TODAY)
    after = revenue_series([_invoice(project, TODAY, work_day=TODAY, **flags)], [project], work, "month", today=TODAY)
    assert before["total"] == after["total"] == 4000


def test_kpi_revenue_and_hourly_rate_are_net(project):
    paid = _invoice(project, TODAY, work_day=TODAY - datetime.timedelta(days=1), sent=True, paid=True)
    kpis = compute_kpis(
        [paid], [project.contract], [project], time_data=_work(project.tag, TODAY - datetime.timedelta(days=1))
    )
    assert kpis.total_revenue == kpis.total_revenue_ytd == 4000
    assert kpis.effective_hourly_rate == 100


def test_outstanding_is_what_the_client_owes(project):
    kpis = compute_kpis([_invoice(project, TODAY, sent=True)], [project.contract], [project])
    assert kpis.outstanding_amount == Decimal("4760")


def test_goals_measure_net_revenue(project):
    paid = _invoice(project, TODAY, sent=True, paid=True)
    totals = DashboardIntent.__new__(DashboardIntent)._revenue_by_target_year([paid], "EUR")
    assert totals == {TODAY.year: Decimal("4000")}
