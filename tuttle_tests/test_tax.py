"""Tests for data-driven tax system and tax reserve calculations."""

import datetime
from decimal import Decimal

import pytest

from tuttle import tax
from tuttle.kpi import monthly_spendable_breakdown
from tuttle.model import (
    Address,
    Client,
    Contract,
    Invoice,
    InvoiceItem,
    Project,
    RecurringExpense,
)
from tuttle.tax import TaxSystem, available_years, get_tax_system, supported_countries
from tuttle.tax_reserves import (
    compute_income_tax_reserve,
    compute_spendable_income,
    compute_vat_reserves,
    monthly_vat_breakdown,
)
from tuttle.time import Cycle

# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def german_tax():
    """Current-year German tax system."""
    return get_tax_system("Germany")


@pytest.fixture
def german_tax_2024():
    return get_tax_system("Germany", date=datetime.date(2024, 6, 1))


@pytest.fixture
def german_tax_2025():
    return get_tax_system("Germany", date=datetime.date(2025, 6, 1))


@pytest.fixture
def german_tax_2026():
    return get_tax_system("Germany", date=datetime.date(2026, 6, 1))


def _sample_country(currency: str = "EUR") -> str:
    """Return a supported country whose tax currency matches *currency*."""
    for country in supported_countries():
        if get_tax_system(country).currency == currency:
            return country
    raise AssertionError(f"No supported country with currency {currency}")


def _tax_system(country: str | None = None):
    return get_tax_system(country or _sample_country())


def _income_below_allowance(tax_system) -> Decimal:
    """Net income safely below the configured basic allowance."""
    allowance = Decimal(str(tax_system.params.basic_allowance))
    if allowance <= 0:
        return Decimal("1000")
    margin = min(Decimal("500"), allowance / 2)
    return (allowance - margin).quantize(Decimal("0.01"))


def _income_above_allowance(tax_system) -> Decimal:
    """Net income safely above the configured basic allowance."""
    allowance = Decimal(str(tax_system.params.basic_allowance))
    return (allowance + Decimal("10000")).quantize(Decimal("0.01"))


def _invoice_items_for_net(net: Decimal, unit_price: int = 100) -> list:
    """Build one invoice line whose subtotal equals *net* (before VAT)."""
    qty = max(int(net / unit_price), 1)
    return [(qty, unit_price, 0)]


def _expected_income_tax_reserve(income: Decimal, country: str, deductions: Decimal = Decimal(0)):
    """Mirror compute_income_tax_reserve using the loaded tax system."""
    tax_system = get_tax_system(country)
    taxable = income - deductions
    if taxable <= 0:
        return Decimal(0), Decimal(0), Decimal(0)
    annual_tax = tax_system.income_tax(taxable)
    annual_soli = tax_system.solidarity_surcharge(annual_tax)
    total = (annual_tax + annual_soli).quantize(Decimal("0.01"))
    return annual_tax, annual_soli, total


def _make_invoice(date, items_data, cancelled=False, vat_rate=None):
    """Create a minimal Invoice with InvoiceItems for testing.

    items_data: list of (quantity, unit_price, vat_rate) tuples.
    If vat_rate is given, it overrides the rate in each item tuple.
    """
    if vat_rate is None:
        vat_rate = get_tax_system(_sample_country()).vat_rate_standard()

    client = Client(
        name="Test Client",
        address=Address(
            street="Test St",
            number="1",
            city="Berlin",
            postal_code="10115",
            country="Germany",
        ),
    )
    contract = Contract(
        title="Test Contract",
        client=client,
        rate=Decimal("100"),
        currency="EUR",
        unit="hour",
        units_per_workday=8,
        term_of_payment=30,
        VAT_rate=Decimal(str(vat_rate)),
    )
    project = Project(title="Test Project", tag="test", contract=contract)
    invoice = Invoice(
        number=f"INV-{date.isoformat()}",
        date=date,
        contract=contract,
        project=project,
        cancelled=cancelled,
        sent=True,
        paid=True,
    )
    for qty, price, _item_vat in items_data:
        InvoiceItem(
            invoice=invoice,
            start_date=date,
            end_date=date,
            quantity=qty,
            unit="hour",
            unit_price=Decimal(str(price)),
            VAT_rate=Decimal(str(vat_rate)),
            description="Test item",
        )
    return invoice


# ── TaxSystem framework ──────────────────────────────────────


class TestTaxSystemFramework:
    def test_get_tax_system_germany(self):
        system = get_tax_system("Germany")
        assert isinstance(system, TaxSystem)
        assert system.country == "Germany"

    def test_get_tax_system_deutschland(self):
        system = get_tax_system("Deutschland")
        assert isinstance(system, TaxSystem)
        assert system.country == "Germany"

    def test_get_tax_system_unsupported(self):
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            get_tax_system("Narnia")

    def test_supported_countries(self):
        countries = supported_countries()
        assert "Germany" in countries

    def test_available_years(self):
        years = available_years("Germany")
        assert 2024 in years
        assert 2025 in years
        assert 2026 in years

    def test_year_selection(self):
        """Different dates yield different year parameters."""
        sys_2024 = get_tax_system("Germany", date=datetime.date(2024, 7, 1))
        sys_2026 = get_tax_system("Germany", date=datetime.date(2026, 7, 1))
        assert sys_2024.year == 2024
        assert sys_2026.year == 2026
        # Basic allowance increased 2024 → 2026
        assert sys_2024.params.basic_allowance < sys_2026.params.basic_allowance

    def test_year_fallback(self):
        """Year without data falls back to nearest available."""
        sys = get_tax_system("Germany", date=datetime.date(2030, 1, 1))
        # Should get the latest available year
        assert sys.year == max(available_years("Germany"))


# ── German income tax ────────────────────────────────────────


class TestGermanIncomeTax:
    def test_zero_income(self, german_tax):
        assert german_tax.income_tax(Decimal(0)) == 0

    def test_below_basic_allowance(self, german_tax_2026):
        """Income below basic allowance (12,096€ for 2026) → 0 tax."""
        assert german_tax_2026.income_tax(Decimal("10000")) == 0
        assert german_tax_2026.income_tax(Decimal("12096")) == 0

    def test_just_above_basic_allowance(self, german_tax):
        """Income just above basic allowance → small tax."""
        allowance = german_tax.params.basic_allowance
        tax_amount = german_tax.income_tax(Decimal(str(allowance + 200)))
        assert tax_amount > 0
        assert tax_amount < 100

    def test_zone2(self, german_tax):
        """Income in zone 2 → moderate tax."""
        tax_amount = german_tax.income_tax(Decimal("15000"))
        assert tax_amount > 0
        assert tax_amount < 2000

    def test_zone3(self, german_tax):
        """Income in zone 3 → progressive tax."""
        tax_amount = german_tax.income_tax(Decimal("50000"))
        assert 10000 < tax_amount < 15000

    def test_zone4(self, german_tax):
        """Income in zone 4 → 42% marginal rate."""
        tax_amount = german_tax.income_tax(Decimal("100000"))
        assert 25000 < tax_amount < 35000

    def test_zone5(self, german_tax):
        """Income above top threshold → 45% marginal rate."""
        tax_amount = german_tax.income_tax(Decimal("300000"))
        assert tax_amount > 100000

    def test_progressive_nature(self, german_tax):
        """Higher income → higher effective rate."""
        rate_30k = german_tax.income_tax(Decimal("30000")) / 30000
        rate_80k = german_tax.income_tax(Decimal("80000")) / 80000
        rate_200k = german_tax.income_tax(Decimal("200000")) / 200000
        assert rate_30k < rate_80k < rate_200k

    def test_backward_compat_function(self):
        """Legacy income_tax() and income_tax_germany() still work."""
        amount1 = tax.income_tax(Decimal("50000"), "Germany")
        amount2 = tax.income_tax_germany(Decimal("50000"))
        assert amount1 == amount2

    def test_different_years_different_tax(self):
        """Tax for same income should differ between years due to allowance changes."""
        income = Decimal("40000")
        tax_2024 = get_tax_system("Germany", datetime.date(2024, 1, 1)).income_tax(income)
        tax_2026 = get_tax_system("Germany", datetime.date(2026, 1, 1)).income_tax(income)
        # Higher basic allowance in 2026 means slightly less tax
        assert tax_2026 < tax_2024


# ── Solidarity surcharge ──────────────────────────────────────


class TestSolidaritySurcharge:
    def test_zero_tax(self, german_tax):
        assert german_tax.solidarity_surcharge(Decimal(0)) == 0

    def test_standard_case(self, german_tax):
        tax_amount = Decimal("10000")
        soli = german_tax.solidarity_surcharge(tax_amount)
        assert soli == Decimal("550.00")

    def test_total_tax(self, german_tax):
        """total_tax = income_tax + soli."""
        income = Decimal("50000")
        it = german_tax.income_tax(income)
        soli = german_tax.solidarity_surcharge(it)
        total = german_tax.total_tax(income)
        assert total == it + soli


# ── VAT ───────────────────────────────────────────────────────


class TestGermanVAT:
    def test_standard_rate(self, german_tax):
        assert german_tax.vat_rate_standard() == Decimal("0.19")

    def test_reduced_rate(self, german_tax):
        assert german_tax.vat_rate_reduced() == Decimal("0.07")


# ── VAT reserves ──────────────────────────────────────────────


class TestVATReserves:
    def test_basic_vat_reserve(self):
        invoices = [
            _make_invoice(datetime.date(2026, 1, 15), [(10, 100, 0.19)]),
            _make_invoice(datetime.date(2026, 2, 15), [(5, 200, 0.19)]),
        ]
        result = compute_vat_reserves(
            invoices,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 3, 31),
        )
        assert result.vat_collected > 0
        assert result.invoice_count == 2

    def test_excludes_cancelled(self):
        invoices = [
            _make_invoice(datetime.date(2026, 1, 15), [(10, 100, 0.19)]),
            _make_invoice(datetime.date(2026, 2, 15), [(5, 200, 0.19)], cancelled=True),
        ]
        result = compute_vat_reserves(
            invoices,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 3, 31),
        )
        assert result.invoice_count == 1

    def test_excludes_out_of_period(self):
        invoices = [
            _make_invoice(datetime.date(2025, 12, 15), [(10, 100, 0.19)]),
            _make_invoice(datetime.date(2026, 1, 15), [(5, 200, 0.19)]),
        ]
        result = compute_vat_reserves(
            invoices,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 3, 31),
        )
        assert result.invoice_count == 1

    def test_empty_invoices(self):
        result = compute_vat_reserves([], datetime.date(2026, 1, 1), datetime.date(2026, 3, 31))
        assert result.vat_collected == Decimal(0)
        assert result.invoice_count == 0


# ── Income tax reserve ────────────────────────────────────────


class TestIncomeTaxReserve:
    def test_basic_reserve(self):
        country = _sample_country()
        tax_system = _tax_system(country)
        income = _income_above_allowance(tax_system)
        result = compute_income_tax_reserve(income, country)
        exp_tax, exp_soli, exp_total = _expected_income_tax_reserve(income, country)

        assert result.estimated_annual_tax == exp_tax
        assert result.solidarity_surcharge == exp_soli
        assert result.total_annual_reserve == exp_tax + exp_soli
        assert result.ytd_reserve == exp_total
        if income > 0 and exp_total > 0:
            assert result.effective_rate == (exp_total / income).quantize(Decimal("0.0001"))

    def test_zero_revenue(self):
        country = _sample_country()
        result = compute_income_tax_reserve(Decimal(0), country)
        assert result.estimated_annual_tax == 0
        assert result.ytd_reserve == 0

    def test_negative_revenue(self):
        country = _sample_country()
        result = compute_income_tax_reserve(Decimal("-5000"), country)
        assert result.estimated_annual_tax == 0

    def test_no_annualization(self):
        """Tax reserve equals full tax on the given income (no proration)."""
        country = _sample_country()
        income = _income_above_allowance(_tax_system(country))
        result = compute_income_tax_reserve(income, country)
        _, _, exp_total = _expected_income_tax_reserve(income, country)
        assert result.ytd_reserve == exp_total

    def test_below_allowance_zero_tax(self):
        country = _sample_country()
        income = _income_below_allowance(_tax_system(country))
        result = compute_income_tax_reserve(income, country)
        assert result.estimated_annual_tax == 0
        assert result.ytd_reserve == 0


# ── Spendable income ──────────────────────────────────────────


class TestSpendableIncome:
    def test_basic_spendable(self):
        """Taxable income reduces spendable by the configured reserve."""
        country = _sample_country()
        tax_system = _tax_system(country)
        net_target = _income_above_allowance(tax_system)
        today = datetime.date.today()
        invoices = [
            _make_invoice(today.replace(day=1), _invoice_items_for_net(net_target)),
        ]
        result = compute_spendable_income(invoices, country)
        _, _, expected_tax = _expected_income_tax_reserve(
            result.received_net + result.outstanding_net + result.planned_revenue,
            country,
        )

        assert result.gross_revenue_ytd > 0
        assert result.vat_reserve > 0
        assert result.net_revenue_ytd == result.gross_revenue_ytd - result.vat_reserve
        # No expenses → business_expenses=0, taxable_profit=net+planned
        assert result.business_expenses == 0
        assert result.taxable_profit == result.net_revenue_ytd + result.planned_revenue
        assert result.income_tax_reserve == expected_tax
        assert expected_tax > 0
        assert result.spendable < result.net_revenue_ytd
        assert result.spendable == result.taxable_profit - result.income_tax_reserve

    def test_below_allowance_zero_tax(self):
        """Income below allowance → no tax reserve, spendable equals net."""
        country = _sample_country()
        net_target = _income_below_allowance(_tax_system(country))
        today = datetime.date.today()
        invoices = [
            _make_invoice(today.replace(day=1), _invoice_items_for_net(net_target)),
        ]
        result = compute_spendable_income(invoices, country)
        assert result.income_tax_reserve == 0
        assert result.spendable == result.net_revenue_ytd + result.planned_revenue

    def test_received_vs_outstanding_breakdown(self):
        """Paid invoices go into received, unpaid into outstanding."""
        country = _sample_country()
        today = datetime.date.today()
        paid_inv = _make_invoice(today.replace(day=1), [(100, 100, 0)])
        unpaid_inv = _make_invoice(today.replace(day=1), [(50, 100, 0)])
        unpaid_inv.paid = False
        result = compute_spendable_income([paid_inv, unpaid_inv], country)
        assert result.received_gross == paid_inv.total
        assert result.outstanding_gross == unpaid_inv.total
        assert result.received_net == paid_inv.total - paid_inv.VAT_total
        assert result.outstanding_net == unpaid_inv.total - unpaid_inv.VAT_total
        assert result.gross_revenue_ytd == paid_inv.total + unpaid_inv.total

    def test_spendable_excludes_cancelled(self):
        country = _sample_country()
        today = datetime.date.today()
        invoices = [
            _make_invoice(today.replace(day=1), [(100, 100, 0)]),
            _make_invoice(today.replace(day=1), [(50, 100, 0)], cancelled=True),
        ]
        result = compute_spendable_income(invoices, country)
        expected_gross = invoices[0].total
        assert result.gross_revenue_ytd == expected_gross

    def test_spendable_excludes_previous_year(self):
        country = _sample_country()
        today = datetime.date.today()
        invoices = [
            _make_invoice(datetime.date(today.year - 1, 6, 1), [(100, 100, 0)]),
            _make_invoice(today.replace(day=1), [(50, 100, 0)]),
        ]
        result = compute_spendable_income(invoices, country)
        assert result.gross_revenue_ytd == invoices[1].total

    def test_monthly_spendable_breakdown_includes_vat_subtraction(self):
        country = _sample_country()
        today = datetime.date.today()
        invoices = [
            _make_invoice(today.replace(day=1), [(20, 100, 0)]),
        ]
        monthly = monthly_spendable_breakdown(invoices, country=country, n_months=2)
        this_month = [m for m in monthly if m["month"] == today.strftime("%Y-%m")][0]
        assert this_month["gross_revenue"] > 0
        assert this_month["vat_due"] > 0
        assert this_month["net_revenue"] == this_month["gross_revenue"] - this_month["vat_due"]
        assert this_month["spendable"] == this_month["net_revenue"] - this_month["income_tax_true_up"]

    def test_spendable_with_expenses(self):
        """Business expenses reduce taxable profit and therefore tax."""
        today = datetime.date.today()
        invoices = [
            _make_invoice(today.replace(day=1), [(100, 100, 0.19)]),
        ]
        expenses = [
            RecurringExpense(
                title="Health Insurance",
                amount=Decimal("500"),
                currency="EUR",
                period=Cycle.monthly,
                category="insurance",
            ),
        ]
        result_no_exp = compute_spendable_income(invoices, "Germany")
        result_with_exp = compute_spendable_income(invoices, "Germany", expenses=expenses)

        # Expenses should be positive
        assert result_with_exp.business_expenses > 0
        # Taxable profit = net_revenue - business_expenses
        assert result_with_exp.taxable_profit == result_with_exp.net_revenue_ytd - result_with_exp.business_expenses
        # Tax should be lower with expenses (smaller tax base)
        assert result_with_exp.income_tax_reserve <= result_no_exp.income_tax_reserve
        # Spendable = taxable_profit - income_tax_reserve
        assert result_with_exp.spendable == result_with_exp.taxable_profit - result_with_exp.income_tax_reserve
        # Net revenue unchanged (expenses don't affect gross/vat)
        assert result_with_exp.net_revenue_ytd == result_no_exp.net_revenue_ytd

    def test_spendable_with_yearly_expense(self):
        """Yearly expenses are normalized to monthly before YTD proration."""
        today = datetime.date.today()
        invoices = [
            _make_invoice(today.replace(day=1), [(100, 100, 0.19)]),
        ]
        monthly_exp = [
            RecurringExpense(
                title="Insurance",
                amount=Decimal("100"),
                currency="EUR",
                period=Cycle.monthly,
            ),
        ]
        yearly_exp = [
            RecurringExpense(
                title="Insurance",
                amount=Decimal("1200"),
                currency="EUR",
                period=Cycle.yearly,
            ),
        ]
        r_monthly = compute_spendable_income(invoices, "Germany", expenses=monthly_exp)
        r_yearly = compute_spendable_income(invoices, "Germany", expenses=yearly_exp)
        # €1200/year normalizes to €100/month — same result
        assert r_monthly.business_expenses == r_yearly.business_expenses
        assert r_monthly.taxable_profit == r_yearly.taxable_profit

    def test_spendable_empty_expenses_same_as_none(self):
        """Empty list behaves like no expenses."""
        today = datetime.date.today()
        invoices = [
            _make_invoice(today.replace(day=1), [(100, 100, 0.19)]),
        ]
        r_none = compute_spendable_income(invoices, "Germany")
        r_empty = compute_spendable_income(invoices, "Germany", expenses=[])
        assert r_none.business_expenses == r_empty.business_expenses == Decimal(0)
        assert r_none.taxable_profit == r_empty.taxable_profit
        assert r_none.spendable == r_empty.spendable


# ── Monthly VAT breakdown ─────────────────────────────────────


class TestMonthlyVAT:
    def test_twelve_months(self):
        invoices = [
            _make_invoice(datetime.date(2026, 1, 15), [(10, 100, 0.19)]),
            _make_invoice(datetime.date(2026, 5, 15), [(20, 100, 0.19)]),
            _make_invoice(datetime.date(2026, 9, 15), [(30, 100, 0.19)]),
        ]
        result = monthly_vat_breakdown(invoices, year=2026)
        assert len(result) == 12
        assert result[0]["month"] == "Jan"
        assert result[0]["invoice_count"] == 1
        assert result[4]["month"] == "May"
        assert result[4]["invoice_count"] == 1
        assert result[8]["month"] == "Sep"
        assert result[8]["invoice_count"] == 1
        assert result[11]["month"] == "Dec"
        assert result[11]["invoice_count"] == 0

    def test_defaults_to_current_year(self):
        result = monthly_vat_breakdown([], year=None)
        assert len(result) == 12
        assert result[0]["period_start"].year == datetime.date.today().year


# ── Spanish tax system (validates marginal_brackets formula) ──


@pytest.fixture
def spanish_tax():
    """Current-year Spanish tax system."""
    return get_tax_system("Spain")


class TestSpanishTaxSystem:
    def test_get_tax_system_spain(self):
        system = get_tax_system("Spain")
        assert isinstance(system, TaxSystem)
        assert system.country == "Spain"

    def test_get_tax_system_espana_alias(self):
        system = get_tax_system("España")
        assert system.country == "Spain"

    def test_available_years_spain(self):
        years = available_years("Spain")
        assert 2024 in years
        assert 2025 in years
        assert 2026 in years

    def test_supported_countries_includes_spain(self):
        countries = supported_countries()
        assert "Spain" in countries
        assert "Germany" in countries


class TestSpanishIncomeTax:
    def test_zero_income(self, spanish_tax):
        assert spanish_tax.income_tax(Decimal(0)) == 0

    def test_below_personal_allowance(self, spanish_tax):
        """Income below mínimo personal (5,550€) → 0 tax."""
        assert spanish_tax.income_tax(Decimal("5000")) == 0
        assert spanish_tax.income_tax(Decimal("5550")) == 0

    def test_first_bracket(self, spanish_tax):
        """Income in first bracket (19% on income above 5,550€ up to 12,450+5,550)."""
        # 10,000€ income → 4,450€ taxable at 19% = 845.50 → rounds to 846
        tax_amount = spanish_tax.income_tax(Decimal("10000"))
        assert tax_amount > 0
        assert tax_amount < 1000

    def test_manual_calculation_20000(self, spanish_tax):
        """Manual check: 20,000€ income, personal allowance 5,550€.
        Taxable = 14,450€
        First 12,450€ at 19% = 2,365.50
        Next 2,000€ at 24% = 480.00
        Total = 2,845.50 → 2846
        """
        tax_amount = spanish_tax.income_tax(Decimal("20000"))
        assert 2800 < tax_amount < 2900

    def test_manual_calculation_50000(self, spanish_tax):
        """Manual check: 50,000€ income, personal allowance 5,550€.
        Taxable = 44,450€
        First 12,450€ at 19% = 2,365.50
        Next 7,750€ (20,200-12,450) at 24% = 1,860.00
        Next 15,000€ (35,200-20,200) at 30% = 4,500.00
        Next 9,250€ (44,450-35,200) at 37% = 3,422.50
        Total = 12,148.00 → 12148
        """
        tax_amount = spanish_tax.income_tax(Decimal("50000"))
        assert 12100 < tax_amount < 12200

    def test_top_bracket(self, spanish_tax):
        """Very high income hits the 47% top marginal rate."""
        tax_amount = spanish_tax.income_tax(Decimal("500000"))
        assert tax_amount > 200000

    def test_progressive_nature(self, spanish_tax):
        """Higher income → higher effective rate."""
        rate_20k = spanish_tax.income_tax(Decimal("20000")) / 20000
        rate_60k = spanish_tax.income_tax(Decimal("60000")) / 60000
        rate_200k = spanish_tax.income_tax(Decimal("200000")) / 200000
        assert rate_20k < rate_60k < rate_200k

    def test_no_solidarity_surcharge(self, spanish_tax):
        """Spain has no solidarity surcharge."""
        tax_amount = spanish_tax.income_tax(Decimal("50000"))
        soli = spanish_tax.solidarity_surcharge(tax_amount)
        assert soli == 0
        # total_tax equals income_tax for Spain
        assert spanish_tax.total_tax(Decimal("50000")) == tax_amount


class TestSpanishVAT:
    def test_standard_rate(self, spanish_tax):
        assert spanish_tax.vat_rate_standard() == Decimal("0.21")

    def test_reduced_rate(self, spanish_tax):
        assert spanish_tax.vat_rate_reduced() == Decimal("0.10")


class TestSpanishReserves:
    def test_income_tax_reserve_spain(self):
        country = "Spain"
        tax_system = get_tax_system(country)
        income = _income_above_allowance(tax_system)
        result = compute_income_tax_reserve(income, country)
        exp_tax, exp_soli, exp_total = _expected_income_tax_reserve(income, country)

        assert result.estimated_annual_tax == exp_tax
        assert result.solidarity_surcharge == exp_soli
        assert result.total_annual_reserve == exp_total
        if income > 0 and exp_total > 0:
            assert result.effective_rate == (exp_total / income).quantize(Decimal("0.0001"))

    def test_spendable_income_spain(self):
        country = "Spain"
        tax_system = get_tax_system(country)
        net_target = _income_above_allowance(tax_system)
        today = datetime.date.today()
        vat = tax_system.vat_rate_standard()
        invoices = [
            _make_invoice(
                today.replace(day=1),
                _invoice_items_for_net(net_target),
                vat_rate=vat,
            ),
        ]
        result = compute_spendable_income(invoices, country)
        _, _, expected_tax = _expected_income_tax_reserve(
            result.received_net + result.outstanding_net + result.planned_revenue,
            country,
        )

        assert result.gross_revenue_ytd > 0
        assert result.vat_reserve > 0
        assert result.income_tax_reserve == expected_tax
        assert expected_tax > 0
        assert result.spendable < result.net_revenue_ytd


class TestCrossCountryComparison:
    def test_different_tax_for_same_income(self):
        """Each supported country can compute tax on the same income."""
        eur_countries = [c for c in supported_countries() if get_tax_system(c).currency == "EUR"]
        assert len(eur_countries) >= 2
        income = _income_above_allowance(_tax_system(eur_countries[0]))
        for country in eur_countries[:2]:
            amount = get_tax_system(country).income_tax(income)
            assert amount >= 0

    def test_vat_rates_loaded_per_country(self):
        """Each country exposes standard VAT rates from tax data."""
        for country in supported_countries():
            rate = get_tax_system(country).vat_rate_standard()
            assert rate >= 0
