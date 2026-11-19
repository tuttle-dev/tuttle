"""A draft invoice is not invoiced yet: no figure counts it, and its tracked time stays planned."""

import datetime
from decimal import Decimal

import pandas
import pytest
import sqlmodel

from tuttle.app.timeline.intent import TimelineIntent
from tuttle.forecasting import cash_flow_series, contracted_revenue, revenue_series
from tuttle.kpi import compute_kpis
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project, Timesheet
from tuttle.tax_reserves import compute_effective_salary, compute_spendable_income, monthly_vat_breakdown
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()
# Mid-year work belongs to this year's planned revenue whatever today's date.
WORK_DAY = datetime.date(TODAY.year, 6, 15)


@pytest.fixture
def project():
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
        VAT_rate=Decimal("0.19"),
        title="Heating",
        client=client,
        start_date=datetime.date(TODAY.year - 1, 1, 1),
        end_date=datetime.date(TODAY.year + 1, 12, 31),
        rate=Decimal("100.00"),
        currency="EUR",
        unit=TimeUnit.hour,
        units_per_workday=8,
        volume=100,
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


def _time_data(tag: str, day: datetime.date) -> pandas.DataFrame:
    begin = datetime.datetime(day.year, day.month, day.day, 9)
    df = pandas.DataFrame(
        {
            "begin": [begin],
            "end": [begin + datetime.timedelta(hours=8)],
            "title": ["Work"],
            "tag": [tag],
            "description": [""],
            "all_day": [False],
        }
    )
    df["duration"] = df["end"] - df["begin"]
    return df.set_index("begin")


def _invoice(project, date: datetime.date, *, work_day: datetime.date = None, **flags) -> Invoice:
    """An invoice for 8 h at 100 + 19% VAT, with a timesheet covering *work_day* if given."""
    inv = Invoice(number="2026-001", date=date, contract=project.contract, project=project, **flags)
    InvoiceItem(
        invoice=inv, quantity=8, unit="hour", unit_price=Decimal("100.00"), VAT_rate=Decimal("0.19"), description="Work"
    )
    if work_day:
        Timesheet(title="ts", date=date, period_start=work_day, period_end=work_day, project=project, invoice=inv)
    return inv


def test_a_draft_is_not_issued_until_sent_or_paid(project):
    assert not _invoice(project, TODAY).is_issued
    assert _invoice(project, TODAY, sent=True).is_issued
    assert _invoice(project, TODAY, paid=True).is_issued


def test_draft_work_stays_planned_on_the_revenue_chart(project):
    td = _time_data(project.tag, TODAY)
    planned = revenue_series([], [project], td, "month", today=TODAY)
    draft = revenue_series([_invoice(project, TODAY, work_day=TODAY)], [project], td, "month", today=TODAY)
    sent = revenue_series([_invoice(project, TODAY, work_day=TODAY, sent=True)], [project], td, "month", today=TODAY)

    assert sum(b["planned"] for b in draft["buckets"]) == 800
    assert draft["total"] == planned["total"]
    assert sum(b["invoiced"] for b in draft["buckets"]) == 0
    assert sum(b["planned"] for b in sent["buckets"]) == 0
    assert sum(b["invoiced"] for b in sent["buckets"]) > 0


def test_kpis_count_no_draft_as_outstanding_or_overdue(project):
    old = TODAY - datetime.timedelta(days=60)
    kpis = compute_kpis([_invoice(project, old)], [project.contract], [project], country="Germany")
    assert (kpis.outstanding_amount, kpis.unpaid_invoices, kpis.overdue_amount, kpis.overdue_invoices) == (0, 0, 0, 0)

    kpis = compute_kpis([_invoice(project, old, sent=True)], [project.contract], [project], country="Germany")
    assert kpis.unpaid_invoices == kpis.overdue_invoices == 1


def test_a_paid_invoice_counts_even_if_never_marked_sent(project):
    kpis = compute_kpis([_invoice(project, TODAY, paid=True)], [project.contract], [project], country="Germany")
    assert kpis.total_revenue > 0


def test_tax_view_counts_draft_work_as_planned_not_invoiced(project):
    draft = _invoice(project, TODAY, work_day=WORK_DAY)
    spending = compute_spendable_income(
        [draft], "Germany", currency="EUR", projects=[project], time_data=_time_data(project.tag, WORK_DAY)
    )
    assert spending.outstanding_gross == 0
    assert spending.vat_reserve == 0
    assert spending.planned_revenue == 800


def test_monthly_vat_has_none_from_drafts(project):
    months = monthly_vat_breakdown([_invoice(project, TODAY)], year=TODAY.year, currency="EUR")
    assert sum(m["vat_collected"] for m in months) == 0
    assert sum(m["invoice_count"] for m in months) == 0


def test_salary_counts_no_draft(project):
    last_month = TODAY.replace(day=1) - datetime.timedelta(days=1)
    paid = _invoice(project, last_month, paid=True)
    with_draft = compute_effective_salary([paid, _invoice(project, last_month)], [], "Germany", currency="EUR")
    without = compute_effective_salary([paid], [], "Germany", currency="EUR")
    assert with_draft == without


def test_cash_flow_receives_draft_work_as_planned(project):
    project.contract.id = 1
    draft = _invoice(project, TODAY, work_day=TODAY)
    cash = cash_flow_series(
        [draft], [project.contract], [project], [], _time_data(project.tag, TODAY), country="Germany", today=TODAY
    )
    assert sum(b["inflow_invoiced"] for b in cash["buckets"]) == 0
    assert sum(b["inflow_planned"] for b in cash["buckets"]) == 800


def test_a_draft_uses_up_none_of_the_contract(project):
    """Agreed 10,000: the draft's 800 are planned, so 9,200 remain contracted, not 8,400."""
    draft = _invoice(project, TODAY, work_day=TODAY)
    slices = contracted_revenue(
        [project], [draft], _time_data(project.tag, TODAY), project.contract.end_date, currency="EUR", today=TODAY
    )
    assert round(sum(s.amount for s in slices), 2) == 9200


def test_timeline_shows_nothing_due_on_a_draft(project):
    engine = sqlmodel.create_engine("sqlite://", echo=False)
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as session:
        session.add(_invoice(project, TODAY - datetime.timedelta(days=60)))
        session.commit()

    intent = TimelineIntent()
    intent.db_engine = engine
    events = intent.get_events(category_filter="invoice").data

    assert events, "the draft itself still appears"
    assert not [e for e in events if e.title.endswith(("due", "overdue"))]
