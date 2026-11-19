"""A year without its own tax rules gets no tax estimate: no other year's rules stand in."""

import datetime
from decimal import Decimal

import pytest

from tuttle import fx
from tuttle.einvoice import _tax_currency
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project, User
from tuttle.tax import NoTaxRules, available_years, get_tax_system, tax_currency
from tuttle.tax_reserves import compute_income_tax_reserve, compute_spendable_income
from tuttle.time import Cycle, TimeUnit

FIRST = available_years("Germany")[0]
LAST = available_years("Germany")[-1]


def _invoice(date: datetime.date, net: str, currency: str = "EUR") -> Invoice:
    client = Client(
        name="Central Services",
        address=Address(street="Main Street", number="42", postal_code="55555", city="Metro", country="Germany"),
    )
    contract = Contract(
        title="Heating",
        client=client,
        rate=Decimal("100"),
        currency=currency,
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    project = Project(title="Boiler", tag="#boiler", start_date=date, contract=contract)
    inv = Invoice(number=f"{date}-1", date=date, contract=contract, project=project, sent=True, paid=True)
    InvoiceItem(invoice=inv, quantity=1, unit="flat", unit_price=Decimal(net), VAT_rate=Decimal("0"), description="Work")
    return inv


@pytest.mark.parametrize("year", [FIRST - 1, LAST + 1])
def test_a_year_before_or_after_the_data_has_no_rules(year):
    with pytest.raises(NoTaxRules, match=rf"^No tax rules for Germany in {year}\.$"):
        get_tax_system("Germany", datetime.date(year, 7, 1))
    with pytest.raises(NoTaxRules, match=rf"^No tax rules for Germany in {year}\.$"):
        compute_income_tax_reserve(Decimal(50000), "Germany", year=year)


def test_an_alias_is_named_by_its_country():
    with pytest.raises(NoTaxRules, match=rf"^No tax rules for Germany in {LAST + 1}\.$"):
        get_tax_system("Deutschland", datetime.date(LAST + 1, 7, 1))


def test_a_year_with_data_is_unaffected():
    assert get_tax_system("Germany", datetime.date(2025, 7, 1)).income_tax(Decimal(50000)) == 10691
    assert compute_income_tax_reserve(Decimal(50000), "Germany", year=2025).ytd_reserve > 0


@pytest.mark.parametrize("year", [FIRST - 1, LAST + 1])
def test_tax_view_shows_no_estimate_for_that_year(year):
    spending = compute_spendable_income([_invoice(datetime.date(year, 3, 1), "40000")], "Germany", currency="EUR", year=year)

    assert spending.net_revenue_ytd == 40000
    assert spending.tax_base == 40000
    assert spending.income_tax_reserve is None
    assert spending.spendable is None
    assert spending.tax_unavailable_reason == f"No tax rules for Germany in {year}."


def test_the_currency_does_not_depend_on_the_year():
    assert tax_currency("United States") == "USD"
    assert tax_currency("Deutschland") == "EUR"
    with pytest.raises(NoTaxRules):
        tax_currency("Norway")
    assert fx.default_currency("United States") == "USD"
    assert fx.default_currency("Norway") == "NOK"
    assert _tax_currency(User(operating_country="United States")) == "USD"


def test_without_a_currency_a_year_without_rules_still_converts():
    """Foreign revenue is converted into the country's currency, not summed as it is."""
    year = FIRST - 1
    spending = compute_spendable_income([_invoice(datetime.date(year, 3, 1), "1000", currency="USD")], "Germany", year=year)
    # USD 1,000 at the suite's stub rate of 0.9.
    assert spending.net_revenue_ytd == 900
