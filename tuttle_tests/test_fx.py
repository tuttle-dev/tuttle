"""Mixed-currency aggregates: a USD invoice must count, converted, exactly once."""

import datetime
from decimal import Decimal

import pytest

from tuttle import fx
from tuttle.kpi import compute_kpis
from tuttle.model import Client, Contract, Invoice, InvoiceItem, TaxCategory
from tuttle.tax_reserves import compute_spendable_income
from tuttle.time import Cycle, TimeUnit


@pytest.fixture(autouse=True)
def stub_rates(monkeypatch):
    """Fixed USD→EUR rate, no network, no app.db."""
    monkeypatch.setattr(fx, "primary_currency", lambda country="Germany": "EUR")
    monkeypatch.setattr(fx, "fx_haircut", lambda: Decimal("1.0"))
    monkeypatch.setattr(
        fx,
        "rate",
        lambda base, quote, month: (
            Decimal(1) if base == quote else Decimal("0.9") if base == "USD" else None
        ),
    )
    monkeypatch.setattr(
        fx,
        "convert",
        lambda amount, base, quote, on: (
            Decimal(amount)
            if base == quote
            else (Decimal(amount) * Decimal("0.9")).quantize(Decimal("0.01"))
        ),
    )
    # kpi/tax_reserves bound these at import time.
    import tuttle.kpi
    import tuttle.tax_reserves

    monkeypatch.setattr(tuttle.kpi, "primary_currency", fx.primary_currency)
    monkeypatch.setattr(tuttle.tax_reserves, "convert", fx.convert)
    monkeypatch.setattr(tuttle.tax_reserves, "fx_haircut", fx.fx_haircut)


def _invoice(currency: str, amount: str, vat_rate="0") -> Invoice:
    category = (
        TaxCategory.outside_scope if Decimal(vat_rate) == 0 else TaxCategory.standard
    )
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
    invoice = Invoice(
        number="1", date=today.replace(month=1, day=15), contract=contract
    )
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
    spending = compute_spendable_income(
        [_invoice("USD", "10000")], "Germany", currency="EUR"
    )

    assert spending.gross_revenue_ytd == Decimal("9000.00")  # ECB rate, no haircut
    assert spending.taxable_profit == Decimal("9000.00")
    assert spending.conversion_fee == Decimal("90.00")  # 1% of the converted net
    assert (
        spending.spendable
        == spending.taxable_profit - spending.income_tax_reserve - Decimal("90.00")
    )


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

    monkeypatch.setattr(
        tuttle.tax_reserves, "convert", lambda amount, base, quote, on: None
    )
    spending = compute_spendable_income(
        [_invoice("EUR", "1000"), _invoice("USD", "10000")], "Germany", currency="EUR"
    )

    assert spending.gross_revenue_ytd == Decimal("1000")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
