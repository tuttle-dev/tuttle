"""Tests for tuttle.forecasting and tuttle.kpi modules."""

import datetime
from decimal import Decimal

import pytest
import pandas

from tuttle.model import (
    Address,
    Client,
    Contact,
    Contract,
    Invoice,
    InvoiceItem,
    Project,
    Timesheet,
    TimeTrackingItem,
)
from tuttle.time import Cycle, TimeUnit
from tuttle.forecasting import (
    monthly_revenue_from_contracts,
    revenue_history,
    revenue_curve,
)
from tuttle.kpi import (
    compute_kpis,
    monthly_revenue_breakdown,
    monthly_spendable_breakdown,
    project_budget_status,
    _format_amount_by_currency,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def contact():
    return Contact(
        first_name="Test",
        last_name="Client",
        email="test@example.com",
        address=Address(
            street="Test St",
            number="1",
            postal_code="12345",
            city="Berlin",
            country="Germany",
        ),
    )


@pytest.fixture
def client(contact):
    return Client(
        name="Test Corp",
        invoicing_contact=contact,
        address=Address(
            street="Test Street",
            number="1",
            city="Berlin",
            postal_code="12345",
            country="Germany",
        ),
    )


@pytest.fixture
def active_contract(client):
    today = datetime.date.today()
    return Contract(
        title="Active Contract",
        client=client,
        signature_date=today - datetime.timedelta(days=60),
        start_date=today - datetime.timedelta(days=30),
        end_date=today + datetime.timedelta(days=180),
        rate=Decimal("100.00"),
        currency="EUR",
        unit=TimeUnit.hour,
        units_per_workday=8,
        volume=500,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )


@pytest.fixture
def project(active_contract):
    today = datetime.date.today()
    return Project(
        title="Test Project",
        tag="#TestProject",
        description="A test project",
        start_date=today - datetime.timedelta(days=30),
        end_date=today + datetime.timedelta(days=180),
        contract=active_contract,
    )


@pytest.fixture
def timesheet_with_items(project):
    today = datetime.date.today()
    ts = Timesheet(
        title="Test Timesheet",
        date=today,
        period_start=today - datetime.timedelta(days=30),
        period_end=today,
        project=project,
    )
    for i in range(5):
        item = TimeTrackingItem(
            timesheet=ts,
            begin=datetime.datetime(
                today.year, today.month, max(today.day - 5 + i, 1), 9, 0
            ),
            end=datetime.datetime(
                today.year, today.month, max(today.day - 5 + i, 1), 17, 0
            ),
            duration=datetime.timedelta(hours=8),
            title=f"Work day {i+1}",
            tag="#TestProject",
        )
        ts.items.append(item)
    return ts


@pytest.fixture
def paid_invoice(active_contract, project, timesheet_with_items):
    today = datetime.date.today()
    inv = Invoice(
        number="2026-001",
        date=today - datetime.timedelta(days=15),
        contract=active_contract,
        project=project,
        sent=True,
        paid=True,
        rendered=True,
    )
    inv.items.append(
        InvoiceItem(
            invoice=inv,
            start_date=today - datetime.timedelta(days=30),
            end_date=today,
            quantity=40,
            unit="hour",
            unit_price=Decimal("100.00"),
            description="Development work",
            VAT_rate=Decimal("0.19"),
        )
    )
    timesheet_with_items.invoice = inv
    return inv


@pytest.fixture
def unpaid_invoice(active_contract, project):
    today = datetime.date.today()
    inv = Invoice(
        number="2026-002",
        date=today - datetime.timedelta(days=5),
        contract=active_contract,
        project=project,
        sent=True,
        paid=False,
        rendered=True,
    )
    inv.items.append(
        InvoiceItem(
            invoice=inv,
            start_date=today - datetime.timedelta(days=10),
            end_date=today - datetime.timedelta(days=5),
            quantity=20,
            unit="hour",
            unit_price=Decimal("100.00"),
            description="More work",
            VAT_rate=Decimal("0.19"),
        )
    )
    return inv


@pytest.fixture
def usd_contract(client):
    today = datetime.date.today()
    return Contract(
        title="USD Contract",
        client=client,
        signature_date=today - datetime.timedelta(days=60),
        start_date=today - datetime.timedelta(days=30),
        end_date=today + datetime.timedelta(days=180),
        rate=Decimal("100.00"),
        currency="USD",
        unit=TimeUnit.hour,
        units_per_workday=8,
        volume=500,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )


@pytest.fixture
def usd_project(usd_contract):
    today = datetime.date.today()
    return Project(
        title="USD Project",
        tag="#USDProject",
        description="A USD-billed project",
        start_date=today - datetime.timedelta(days=30),
        end_date=today + datetime.timedelta(days=180),
        contract=usd_contract,
    )


@pytest.fixture
def unpaid_usd_invoice(usd_contract, usd_project):
    today = datetime.date.today()
    inv = Invoice(
        number="2026-USD-001",
        date=today - datetime.timedelta(days=5),
        contract=usd_contract,
        project=usd_project,
        sent=True,
        paid=False,
        rendered=True,
    )
    inv.items.append(
        InvoiceItem(
            invoice=inv,
            start_date=today - datetime.timedelta(days=10),
            end_date=today - datetime.timedelta(days=5),
            quantity=20,
            unit="hour",
            unit_price=Decimal("100.00"),
            description="US client work",
            VAT_rate=Decimal("0.19"),
        )
    )
    return inv


# ── Forecasting Tests ─────────────────────────────────────────


class TestMonthlyRevenueFromContracts:
    def test_empty_contracts(self):
        today = datetime.date.today()
        result = monthly_revenue_from_contracts(
            [], today, today + datetime.timedelta(days=60)
        )
        assert result.empty

    def test_active_contract_produces_rows(self, active_contract, project):
        # project must be attached for the function to pick up the title
        active_contract.projects = [project]
        today = datetime.date.today()
        result = monthly_revenue_from_contracts(
            [active_contract],
            today,
            today + datetime.timedelta(days=90),
        )
        assert not result.empty
        assert "month" in result.columns
        assert "revenue" in result.columns
        assert all(result["revenue"] > 0)

    def test_completed_contract_excluded(self, active_contract, project):
        active_contract.is_completed = True
        active_contract.projects = [project]
        today = datetime.date.today()
        result = monthly_revenue_from_contracts(
            [active_contract],
            today,
            today + datetime.timedelta(days=90),
        )
        assert result.empty

    def test_future_contract_excluded_before_start(self, active_contract, project):
        today = datetime.date.today()
        active_contract.start_date = today + datetime.timedelta(days=100)
        active_contract.end_date = today + datetime.timedelta(days=200)
        active_contract.projects = [project]
        result = monthly_revenue_from_contracts(
            [active_contract],
            today,
            today + datetime.timedelta(days=30),
        )
        assert result.empty


class TestRevenueHistory:
    def test_empty_invoices(self):
        result = revenue_history([])
        assert result.empty

    def test_cancelled_invoices_excluded(self, paid_invoice):
        paid_invoice.cancelled = True
        result = revenue_history([paid_invoice])
        assert result.empty

    def test_paid_invoice_included(self, paid_invoice):
        result = revenue_history([paid_invoice])
        assert not result.empty
        assert result["revenue"].sum() > 0


class TestRevenueCurve:
    def test_combined_history_and_forecast(
        self, paid_invoice, active_contract, project
    ):
        active_contract.projects = [project]
        result = revenue_curve([paid_invoice], [active_contract], forecast_months=3)
        assert not result.empty
        assert "is_forecast" in result.columns
        assert "cumulative_revenue" in result.columns

    def test_empty_data(self):
        result = revenue_curve([], [], forecast_months=3)
        assert result.empty or len(result) == 0


# ── KPI Tests ─────────────────────────────────────────────────


class TestComputeKPIs:
    def test_with_paid_invoice(self, paid_invoice, active_contract, project):
        kpis = compute_kpis([paid_invoice], [active_contract], [project])
        assert kpis.total_revenue > 0
        assert kpis.outstanding_amount == 0
        assert kpis.active_contracts == 1
        assert kpis.active_projects == 1
        assert kpis.unpaid_invoices == 0

    def test_with_unpaid_invoice(self, unpaid_invoice, active_contract, project):
        kpis = compute_kpis([unpaid_invoice], [active_contract], [project])
        assert kpis.total_revenue == 0
        assert kpis.outstanding_amount > 0
        assert kpis.unpaid_invoices == 1

    def test_effective_hourly_rate(self, paid_invoice, active_contract, project):
        kpis = compute_kpis([paid_invoice], [active_contract], [project])
        if kpis.effective_hourly_rate is not None:
            assert kpis.effective_hourly_rate > 0

    def test_empty_data(self):
        kpis = compute_kpis([], [], [])
        assert kpis.total_revenue == 0
        assert kpis.active_projects == 0
        assert kpis.active_contracts == 0

    def test_tax_reserves_populated(self, paid_invoice, active_contract, project):
        kpis = compute_kpis([paid_invoice], [active_contract], [project])
        assert kpis.vat_reserve >= 0
        assert kpis.income_tax_reserve >= 0
        assert kpis.spendable_income <= kpis.total_revenue_ytd
        assert kpis.tax_currency == "EUR"

    def test_spendable_less_than_gross(self, paid_invoice, active_contract, project):
        kpis = compute_kpis([paid_invoice], [active_contract], [project])
        if kpis.total_revenue_ytd > 0:
            assert kpis.spendable_income < kpis.total_revenue_ytd

    def test_empty_data_tax_reserves(self):
        kpis = compute_kpis([], [], [])
        assert kpis.vat_reserve == 0
        assert kpis.income_tax_reserve == 0
        assert kpis.spendable_income == 0

    def test_outstanding_currency_matches_invoice_currency(
        self, unpaid_usd_invoice, usd_contract, usd_project
    ):
        """A USD invoice's outstanding amount must be labeled USD, not EUR.

        Regression test for https://github.com/tuttle-dev/tuttle/issues/400:
        the dashboard previously formatted the outstanding amount using the
        tax system's currency (EUR for Germany) regardless of the invoice's
        actual currency.
        """
        kpis = compute_kpis(
            [unpaid_usd_invoice], [usd_contract], [usd_project], country="Germany"
        )
        assert kpis.tax_currency == "EUR"
        assert kpis.outstanding_by_currency == {"USD": unpaid_usd_invoice.total}
        formatted = kpis.to_rpc_dict()["outstanding_amount_formatted"]
        assert "$" in formatted
        assert "€" not in formatted

    def test_outstanding_amounts_in_different_currencies_not_mixed(
        self,
        unpaid_invoice,
        active_contract,
        project,
        unpaid_usd_invoice,
        usd_contract,
        usd_project,
    ):
        """Outstanding amounts in different currencies must not be summed together."""
        kpis = compute_kpis(
            [unpaid_invoice, unpaid_usd_invoice],
            [active_contract, usd_contract],
            [project, usd_project],
            country="Germany",
        )
        assert kpis.outstanding_by_currency == {
            "EUR": unpaid_invoice.total,
            "USD": unpaid_usd_invoice.total,
        }
        formatted = kpis.to_rpc_dict()["outstanding_amount_formatted"]
        assert "$" in formatted
        assert "€" in formatted

    def test_overdue_currency_matches_invoice_currency(
        self, unpaid_usd_invoice, usd_contract, usd_project
    ):
        """Overdue amounts follow the same per-currency labeling as outstanding."""
        # usd_contract.term_of_payment is 14 days, so an invoice issued 20
        # days ago has a due date 6 days in the past, i.e. it's overdue.
        unpaid_usd_invoice.date = datetime.date.today() - datetime.timedelta(days=20)
        kpis = compute_kpis(
            [unpaid_usd_invoice], [usd_contract], [usd_project], country="Germany"
        )
        assert kpis.overdue_by_currency == {"USD": unpaid_usd_invoice.total}
        formatted = kpis.to_rpc_dict()["overdue_amount_formatted"]
        assert "$" in formatted
        assert "€" not in formatted


class TestFormatAmountByCurrency:
    def test_single_currency_uses_that_currency(self):
        result = _format_amount_by_currency(
            Decimal("100"), {"USD": Decimal("100")}, "EUR"
        )
        assert "$" in result
        assert "€" not in result

    def test_no_breakdown_uses_fallback(self):
        result = _format_amount_by_currency(Decimal("0"), {}, "EUR")
        assert "€" in result

    def test_multiple_currencies_are_not_summed(self):
        result = _format_amount_by_currency(
            Decimal("300"),
            {"USD": Decimal("100"), "EUR": Decimal("200")},
            "EUR",
        )
        assert "$" in result
        assert "€" in result


class TestMonthlyRevenueBreakdown:
    def test_empty_invoices(self):
        result = monthly_revenue_breakdown([])
        assert isinstance(result, list)
        assert len(result) > 0  # should still have month buckets

    def test_with_invoices(self, paid_invoice):
        result = monthly_revenue_breakdown([paid_invoice], n_months=3)
        assert isinstance(result, list)
        total = sum(float(m["revenue"]) for m in result)
        assert total > 0

    def test_cancelled_invoices_excluded(self, paid_invoice):
        paid_invoice.cancelled = True
        result = monthly_revenue_breakdown([paid_invoice], n_months=3)
        total = sum(float(m["revenue"]) for m in result)
        assert total == 0

    def test_n_months_controls_bucket_count(self):
        result_3 = monthly_revenue_breakdown([], n_months=3)
        result_12 = monthly_revenue_breakdown([], n_months=12)
        assert len(result_3) < len(result_12)

    def test_months_are_sorted(self, paid_invoice):
        result = monthly_revenue_breakdown([paid_invoice], n_months=6)
        keys = [m["month"] for m in result]
        assert keys == sorted(keys)

    def test_pipeline_key_present(self):
        result = monthly_revenue_breakdown([], n_months=3)
        for m in result:
            assert "pipeline" in m

    def test_sent_unpaid_goes_to_pipeline(self, unpaid_invoice):
        result = monthly_revenue_breakdown([unpaid_invoice], n_months=3)
        total_revenue = sum(float(m["revenue"]) for m in result)
        total_pipeline = sum(float(m["pipeline"]) for m in result)
        assert total_revenue == 0
        assert total_pipeline > 0

    def test_paid_not_in_pipeline(self, paid_invoice):
        result = monthly_revenue_breakdown([paid_invoice], n_months=3)
        total_pipeline = sum(float(m["pipeline"]) for m in result)
        assert total_pipeline == 0

    def test_unsent_unpaid_excluded_from_both(self, unpaid_invoice):
        unpaid_invoice.sent = False
        result = monthly_revenue_breakdown([unpaid_invoice], n_months=3)
        total_revenue = sum(float(m["revenue"]) for m in result)
        total_pipeline = sum(float(m["pipeline"]) for m in result)
        assert total_revenue == 0
        assert total_pipeline == 0


class TestMonthlySpendableBreakdown:
    def test_with_invoices(self, paid_invoice):
        result = monthly_spendable_breakdown(
            [paid_invoice], country="Germany", n_months=3
        )
        assert isinstance(result, list)
        assert len(result) > 0
        for month in result:
            assert month["net_revenue"] == month["gross_revenue"] - month["vat_due"]
            assert (
                month["spendable"] == month["net_revenue"] - month["income_tax_true_up"]
            )

    def test_empty_invoices(self):
        result = monthly_spendable_breakdown([], country="Germany", n_months=3)
        assert isinstance(result, list)
        assert len(result) > 0
        for month in result:
            assert month["gross_revenue"] == 0
            assert month["vat_due"] == 0
            assert month["net_revenue"] == 0

    def test_true_up_deltas_reconcile(self, paid_invoice, unpaid_invoice):
        today = datetime.date.today()
        paid_invoice.date = today.replace(day=1)
        unpaid_invoice.date = (
            today.replace(day=1) - datetime.timedelta(days=32)
        ).replace(day=1)
        result = monthly_spendable_breakdown(
            [paid_invoice, unpaid_invoice],
            country="Germany",
            n_months=4,
        )
        total_true_up = sum(
            month["income_tax_true_up"]
            for month in result
            if month["month"].startswith(str(today.year))
        )
        assert total_true_up >= 0

    def test_cancelled_invoices_excluded(self, paid_invoice):
        paid_invoice.cancelled = True
        result = monthly_spendable_breakdown(
            [paid_invoice], country="Germany", n_months=3
        )
        for month in result:
            assert month["gross_revenue"] == 0
            assert month["vat_due"] == 0

    def test_spendable_less_than_net(self, paid_invoice):
        """Spendable should be <= net after income tax is subtracted."""
        today = datetime.date.today()
        paid_invoice.date = today.replace(day=1)
        result = monthly_spendable_breakdown(
            [paid_invoice], country="Germany", n_months=3
        )
        this_month = [m for m in result if m["month"] == today.strftime("%Y-%m")]
        if this_month and this_month[0]["net_revenue"] > 0:
            assert this_month[0]["spendable"] <= this_month[0]["net_revenue"]

    def test_spain(self, paid_invoice):
        """Spendable breakdown works with a non-Germany country."""
        result = monthly_spendable_breakdown(
            [paid_invoice], country="Spain", n_months=3
        )
        assert isinstance(result, list)
        assert len(result) > 0
        for month in result:
            assert month["net_revenue"] == month["gross_revenue"] - month["vat_due"]

    def test_non_current_year_months_have_zero_tax(self, paid_invoice):
        """Months in previous years should have zero income_tax_true_up."""
        today = datetime.date.today()
        paid_invoice.date = datetime.date(today.year - 1, 6, 15)
        result = monthly_spendable_breakdown(
            [paid_invoice], country="Germany", n_months=18
        )
        for month in result:
            if not month["month"].startswith(str(today.year)):
                assert month["income_tax_true_up"] == 0

    def test_months_sorted(self, paid_invoice):
        result = monthly_spendable_breakdown(
            [paid_invoice], country="Germany", n_months=6
        )
        keys = [m["month"] for m in result]
        assert keys == sorted(keys)


@pytest.fixture
def time_data_df(project):
    """Calendar DataFrame with past and future events tagged for the test project."""
    today = datetime.date.today()
    records = []
    # 5 past events (8h each)
    for i in range(1, 6):
        d = today - datetime.timedelta(days=i)
        records.append(
            {
                "begin": datetime.datetime(d.year, d.month, d.day, 9, 0),
                "end": datetime.datetime(d.year, d.month, d.day, 17, 0),
                "duration": datetime.timedelta(hours=8),
                "title": f"Past work {i}",
                "tag": "#TestProject",
                "description": "",
                "all_day": False,
            }
        )
    # 2 future events (8h each)
    for i in range(1, 3):
        d = today + datetime.timedelta(days=i)
        records.append(
            {
                "begin": datetime.datetime(d.year, d.month, d.day, 9, 0),
                "end": datetime.datetime(d.year, d.month, d.day, 17, 0),
                "duration": datetime.timedelta(hours=8),
                "title": f"Future work {i}",
                "tag": "#TestProject",
                "description": "",
                "all_day": False,
            }
        )
    df = pandas.DataFrame(records).set_index("begin")
    return df


class TestProjectBudgetStatus:
    def test_project_without_volume_no_time_data(self, project):
        project.contract.volume = None
        result = project_budget_status([project])
        assert result == []

    def test_open_ended_with_time_data(self, project, time_data_df):
        """Open-ended contracts show a full bar with total hours."""
        project.contract.volume = None
        result = project_budget_status([project], time_data=time_data_df)
        assert len(result) == 1
        assert result[0]["open_ended"] is True
        assert result[0]["progress"] == 1.0
        assert result[0]["hours_budget"] == 0.0
        assert result[0]["budget_exceeded"] is False
        assert result[0]["hours_tracked"] == 40.0

    def test_tracked_from_calendar_data(self, project, time_data_df):
        """Past calendar events are the source of truth for hours_tracked."""
        project.contract.volume = 100
        result = project_budget_status([project], time_data=time_data_df)
        assert len(result) == 1
        assert result[0]["project"] == "Test Project"
        assert result[0]["hours_tracked"] == 40.0  # 5 × 8h
        assert result[0]["hours_planned"] == 16.0  # 2 × 8h
        assert 0 <= result[0]["progress"] <= 1.0
        assert result[0]["open_ended"] is False

    def test_no_time_data_yields_empty(self, project):
        """Without calendar data no budget rows are produced."""
        project.contract.volume = 100
        result = project_budget_status([project], time_data=None)
        assert result == []

    def test_empty_projects(self):
        result = project_budget_status([])
        assert result == []
