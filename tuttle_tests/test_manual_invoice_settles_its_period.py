"""An invoice typed in by hand has no timesheet: its billing period is what counts as invoiced."""

import datetime
from decimal import Decimal

import pandas
import pytest

from tuttle.forecasting import revenue_series
from tuttle.kpi import compute_kpis
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project
from tuttle.tax_reserves import compute_planned_revenue
from tuttle.time import ContractType, Cycle, TimeUnit
from tuttle.timetracking import invoiced_ranges_by_tag

TODAY = datetime.date.today()
# Mid-year work belongs to this year's planned revenue whatever today's date.
WORK_DAY = datetime.date(TODAY.year, 6, 15)
JUNE = (datetime.date(TODAY.year, 6, 1), datetime.date(TODAY.year, 6, 30))


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


def _time_data(tag: str, *days: datetime.date) -> pandas.DataFrame:
    """Eight hours of work on each of *days*."""
    begins = [datetime.datetime(day.year, day.month, day.day, 9) for day in days]
    df = pandas.DataFrame(
        {
            "begin": begins,
            "end": [begin + datetime.timedelta(hours=8) for begin in begins],
            "title": "Work",
            "tag": tag,
            "description": "",
            "all_day": False,
        }
    )
    df["duration"] = df["end"] - df["begin"]
    return df.set_index("begin")


def _by_hand(project, period=JUNE, quantity=5, **flags) -> Invoice:
    """An invoice for *quantity* hours typed in by hand for *period*: no timesheet."""
    flags = {"sent": True} | flags
    start, end = period
    inv = Invoice(number="2026-001", date=end, contract=project.contract, project=project, **flags)
    InvoiceItem(
        invoice=inv,
        start_date=start,
        end_date=end,
        quantity=quantity,
        unit="hour",
        unit_price=Decimal("100.00"),
        VAT_rate=Decimal("0.19"),
        description="Work",
    )
    return inv


def _planned(project, invoices, *days) -> Decimal:
    return compute_planned_revenue([project], _time_data(project.tag, *days), currency="EUR", invoices=invoices)


def test_work_in_its_period_is_no_longer_planned(project):
    assert _planned(project, [], WORK_DAY) == 800
    # Fewer hours billed than tracked: the period is settled all the same.
    assert _planned(project, [_by_hand(project)], WORK_DAY) == 0


def test_work_outside_its_period_stays_planned(project):
    july = datetime.date(TODAY.year, 7, 15)
    assert _planned(project, [_by_hand(project)], WORK_DAY, july) == 800


def test_another_projects_work_stays_planned(project):
    other = Project(title="Ducts", tag="#ducts", description="", start_date=WORK_DAY, contract=project.contract)
    time_data = _time_data(other.tag, WORK_DAY)
    assert compute_planned_revenue([project, other], time_data, currency="EUR", invoices=[_by_hand(project)]) == 800


@pytest.mark.parametrize("flags", [{"sent": False}, {"cancelled": True}], ids=["draft", "cancelled"])
def test_a_draft_or_cancelled_one_settles_nothing(project, flags):
    assert _planned(project, [_by_hand(project, **flags)], WORK_DAY) == 800


@pytest.mark.parametrize("document_type", ["reminder", "deposit", "final"])
def test_only_a_regular_invoice_settles_a_period(project, document_type):
    assert invoiced_ranges_by_tag([_by_hand(project, document_type=document_type)]) == {}


def test_a_fixed_price_invoice_settles_no_period(project):
    project.contract.type = ContractType.fixed_price
    project.contract.fixed_price = Decimal("5000")
    assert invoiced_ranges_by_tag([_by_hand(project)]) == {}


def test_an_invoice_without_dates_settles_no_period(project):
    assert invoiced_ranges_by_tag([_by_hand(project, period=(None, None))]) == {}


def test_the_period_spans_all_dated_items(project):
    inv = _by_hand(project)
    InvoiceItem(
        invoice=inv,
        start_date=datetime.date(TODAY.year, 7, 1),
        end_date=datetime.date(TODAY.year, 7, 31),
        quantity=1,
        unit="hour",
        unit_price=Decimal("100.00"),
        VAT_rate=Decimal("0.19"),
        description="More work",
    )
    InvoiceItem(
        invoice=inv, quantity=1, unit="piece", unit_price=Decimal("50.00"), VAT_rate=Decimal("0.19"), description="Parts"
    )
    assert invoiced_ranges_by_tag([inv]) == {"#boiler": [(JUNE[0], datetime.date(TODAY.year, 7, 31))]}


def test_the_revenue_chart_counts_the_work_once(project):
    yesterday = TODAY - datetime.timedelta(days=1)
    period = (yesterday.replace(day=1), yesterday)
    time_data = _time_data(project.tag, yesterday)
    inv = _by_hand(project, period=period, quantity=8)
    inv.date = TODAY

    before = revenue_series([], [project], time_data, "month", today=TODAY)
    after = revenue_series([inv], [project], time_data, "month", today=TODAY)

    assert sum(b["planned"] for b in before["buckets"]) == 800
    assert sum(b["planned"] for b in after["buckets"]) == 0
    assert sum(b["invoiced"] for b in after["buckets"]) == 800


def test_nothing_in_its_period_is_ready_to_invoice(project):
    yesterday = TODAY - datetime.timedelta(days=1)
    if yesterday.year != TODAY.year:
        pytest.skip("Ready to invoice counts this year's work only")
    time_data = _time_data(project.tag, yesterday)
    inv = _by_hand(project, period=(yesterday, yesterday))

    def ready(invoices):
        return compute_kpis(invoices, [project.contract], [project], country="Germany", time_data=time_data).ready_to_invoice

    assert ready([]) == 800
    assert ready([inv]) == 0
