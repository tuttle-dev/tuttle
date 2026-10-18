"""Mixed-currency aggregates: a USD invoice must count, converted, exactly once."""

import datetime
from decimal import Decimal

import pandas
import pytest

from tuttle import fx, tax_reserves
from tuttle.forecasting import revenue_series
from tuttle.kpi import compute_kpis
from tuttle.model import Client, Contract, Invoice, InvoiceItem, Project, RecurringExpense, TaxCategory
from tuttle.tax_reserves import compute_effective_salary, compute_income_tax_reserve, compute_spendable_income
from tuttle.time import Cycle, TimeUnit


@pytest.fixture(autouse=True)
def stub_rates(monkeypatch):
    """Fixed USD→EUR rate, no network, no app.db."""
    monkeypatch.setattr(fx, "primary_currency", lambda country="Germany": "EUR")
    monkeypatch.setattr(fx, "fx_haircut", lambda: Decimal("1.0"))
    monkeypatch.setattr(
        fx,
        "rate",
        lambda base, quote, month: Decimal(1) if base == quote else Decimal("0.9") if base == "USD" else None,
    )
    monkeypatch.setattr(
        fx,
        "convert",
        lambda amount, base, quote, on: (
            Decimal(amount) if base == quote else (Decimal(amount) * Decimal("0.9")).quantize(Decimal("0.01"))
        ),
    )
    # kpi/tax_reserves/forecasting bound these at import time.
    import tuttle.forecasting
    import tuttle.kpi
    import tuttle.tax_reserves

    monkeypatch.setattr(tuttle.forecasting, "primary_currency", fx.primary_currency)
    monkeypatch.setattr(tuttle.forecasting, "convert", fx.convert)
    monkeypatch.setattr(tuttle.kpi, "primary_currency", fx.primary_currency)
    monkeypatch.setattr(tuttle.tax_reserves, "convert", fx.convert)
    monkeypatch.setattr(tuttle.tax_reserves, "fx_haircut", fx.fx_haircut)


def _invoice(currency: str, amount: str, vat_rate="0") -> Invoice:
    category = TaxCategory.outside_scope if Decimal(vat_rate) == 0 else TaxCategory.standard
    contract = Contract(
        title=f"{currency} contract",
        client=Client(name="US Client"),
        rate=Decimal(amount),
        currency=currency,
        VAT_rate=Decimal(vat_rate),
        VAT_category=category,
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    today = datetime.date.today()
    invoice = Invoice(number="1", date=today.replace(month=1, day=15), contract=contract)
    invoice.items = [
        InvoiceItem(
            quantity=1,
            unit="hour",
            unit_price=Decimal(amount),
            description="work",
            VAT_rate=Decimal(vat_rate),
            VAT_category=category,
        )
    ]
    invoice.paid = True
    return invoice


def test_foreign_invoice_is_converted_not_dropped_or_mixed():
    invoices = [_invoice("EUR", "1000"), _invoice("USD", "10000")]

    kpis = compute_kpis(invoices, [], [], country="Germany")

    # 1000 EUR + 10000 USD * 0.9 = 10000 EUR — neither 11000 (mixed) nor 1000 (dropped).
    assert kpis.total_revenue == Decimal("10000")
    assert kpis.tax_currency == "EUR"


def test_conversion_fee_hits_salary_but_not_the_tax_base():
    spending = compute_spendable_income([_invoice("USD", "10000")], "Germany", currency="EUR")

    assert spending.gross_revenue_ytd == Decimal("9000.00")  # ECB rate, no haircut
    assert spending.taxable_profit == Decimal("9000.00")
    assert spending.conversion_fee == Decimal("90.00")  # 1% of the converted net
    assert spending.spendable == spending.taxable_profit - spending.income_tax_reserve - Decimal("90.00")


def test_dashboard_and_tax_view_agree_on_planned_dollar_work():
    contract = _invoice("USD", "100").contract
    project = Project(
        title="Security Review",
        tag="#security",
        description="",
        start_date=datetime.date.today(),
        contract=contract,
    )
    begin = datetime.datetime.combine(datetime.date.today(), datetime.time(9))
    time_data = pandas.DataFrame(
        {
            "end": [begin + datetime.timedelta(hours=8)],
            "title": ["Work"],
            "tag": [project.tag],
            "description": [""],
            "all_day": [False],
        },
        index=pandas.Index([begin], name="begin"),
    )
    time_data["duration"] = time_data["end"] - time_data.index

    chart = revenue_series([], [project], time_data, granularity="year", country="Germany")
    this_year = next(b for b in chart["buckets"] if b["is_current"])
    spending = compute_spendable_income([], "Germany", currency="EUR", projects=[project], time_data=time_data)

    # 8 h × $100 × 0.9 — the same euros in both views.
    assert this_year["planned"] == pytest.approx(720.0)
    assert spending.planned_revenue == Decimal("720.00")


def test_conversion_fee_lowers_the_salary_but_not_its_tax():
    plain = compute_effective_salary([_invoice("EUR", "9000")], [], "Germany", currency="EUR")
    salary = compute_effective_salary([_invoice("USD", "10000")], [], "Germany", currency="EUR")

    assert salary.conversion_fee_monthly > 0
    assert salary.income_tax_reserve_monthly == plain.income_tax_reserve_monthly
    assert salary.optimistic_monthly == plain.optimistic_monthly - salary.conversion_fee_monthly


def test_foreign_currency_expense_is_converted():
    expense = RecurringExpense(
        title="Software", amount=Decimal("100"), currency="USD", period=Cycle.monthly, tax_deductible=True
    )
    invoices = [_invoice("EUR", "9000")]

    salary = compute_effective_salary(invoices, [expense], "Germany", currency="EUR")
    spending = compute_spendable_income(invoices, "Germany", expenses=[expense], currency="EUR")

    assert salary.monthly_expenses == Decimal("90.00")
    assert spending.business_expenses == Decimal("90.00") * 12


class TestCurrencyValidation:
    """A currency we cannot convert must be refused on write, not in a sum."""

    @pytest.fixture(autouse=True)
    def stub_supported(self, monkeypatch):
        monkeypatch.setattr(fx, "supported_currencies", lambda: ("EUR", "GBP", "USD"))

    @pytest.mark.parametrize("code,expected", [("usd", "USD"), (" eur ", "EUR")])
    def test_normalizes_case_and_whitespace(self, code, expected):
        assert fx.validate_currency_code(code) == expected

    @pytest.mark.parametrize("code", ["XYZ", "", None, "BTC"])
    def test_rejects_a_currency_without_rates(self, code):
        with pytest.raises(ValueError, match="Unsupported currency"):
            fx.validate_currency_code(code)

    def test_contract_validation_writes_the_normalized_code_back(self):
        contract = Contract(title="c", currency="usd", start_date=datetime.date.today())
        contract.validate_currency()
        assert contract.currency == "USD"

    def test_contract_rejects_an_unconvertible_currency(self):
        contract = Contract(title="c", currency="XYZ", start_date=datetime.date.today())
        with pytest.raises(ValueError, match="Unsupported currency"):
            contract.validate_currency()


def test_unresolvable_rate_leaves_the_invoice_out_rather_than_zeroing_it(monkeypatch):
    import tuttle.tax_reserves

    monkeypatch.setattr(tuttle.tax_reserves, "convert", lambda amount, base, quote, on: None)
    spending = compute_spendable_income([_invoice("EUR", "1000"), _invoice("USD", "10000")], "Germany", currency="EUR")

    assert spending.gross_revenue_ytd == Decimal("1000")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


@pytest.mark.parametrize(
    "country, currency",
    [
        ("Germany", "EUR"),
        ("Sweden", "SEK"),
        ("United States", "USD"),
        ("Czech Republic", "CZK"),
        ("United Kingdom", "GBP"),
        ("Turkey", "TRY"),
        ("Argentina", "EUR"),  # no ECB rate for ARS, so nothing could convert into it
        ("", "EUR"),
    ],
)
def test_default_currency_is_the_countrys_own(country, currency):
    assert fx.default_currency(country) == currency


class TestMonthStart:
    """Before the ECB's first fixing of a month, foreign amounts must not drop out."""

    @pytest.fixture(autouse=True)
    def fresh_cache(self, monkeypatch, isolated_data_dir):
        today = datetime.date.today()

        def fetch(base, quote, month):
            if (month.year, month.month) >= (today.year, today.month):
                raise fx._NoRatesYet("not fixed yet")
            return Decimal("0.9")

        monkeypatch.setattr(fx, "_fetch_monthly_average", fetch)
        fx._rate.cache_clear()
        yield
        fx._rate.cache_clear()

    def test_the_open_month_uses_last_months_rate(self):
        today = datetime.date.today()
        assert fx._rate("USD", "EUR", f"{today:%Y-%m}") == Decimal("0.9")
        next_month = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        assert fx._rate("USD", "EUR", f"{next_month:%Y-%m}") == Decimal("0.9")


def test_income_tax_is_computed_in_the_tax_systems_currency(monkeypatch):
    monkeypatch.setattr(
        tax_reserves, "fx_rate", lambda base, quote, on: Decimal(11) if (base, quote) == ("EUR", "SEK") else None
    )
    in_eur = compute_income_tax_reserve(Decimal(50000), "Sweden", currency="EUR")
    in_sek = compute_income_tax_reserve(Decimal(550000), "Sweden", currency="SEK")

    assert in_sek.total_annual_reserve > 0
    assert abs(in_eur.total_annual_reserve * 11 - in_sek.total_annual_reserve) < Decimal("0.01")
