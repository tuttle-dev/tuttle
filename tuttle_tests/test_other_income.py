"""Income from outside Tuttle (#645).

A freelancer with a part-time job pays income tax on both incomes together, and
the tax is progressive: the freelance income lands in a higher bracket than it
would alone. Tuttle reserves only the extra tax the freelance income causes,
tax(freelance + other) - tax(other). The other income is not business revenue.
"""

import datetime
from decimal import Decimal

import pytest

from tuttle.model import OtherIncome, RecurringExpense
from tuttle.tax import get_tax_system
from tuttle.tax_reserves import (
    annual_other_income,
    compute_effective_salary,
    compute_income_tax_reserve,
    compute_spendable_income,
)
from tuttle.time import Cycle

from .test_tax import _make_invoice

YEAR = datetime.date.today().year


def _job(amount="3000", period=Cycle.monthly, currency="EUR", title="Part-time job"):
    return OtherIncome(title=title, amount=Decimal(amount), currency=currency, period=period, kind="employment")


def _total_tax(income: Decimal) -> Decimal:
    system = get_tax_system("Germany", datetime.date(YEAR, 7, 1))
    tax = system.income_tax(income)
    return tax + system.solidarity_surcharge(tax)


# ── The reserve ──────────────────────────────────────────────


def test_reserve_is_the_extra_tax_the_freelance_income_causes():
    freelance, other = Decimal("30000"), Decimal("36000")

    reserve = compute_income_tax_reserve(freelance, "Germany", year=YEAR, other_income=other)

    assert reserve.total_annual_reserve == _total_tax(freelance + other) - _total_tax(other)


def test_other_income_raises_the_reserve():
    alone = compute_income_tax_reserve(Decimal("30000"), "Germany", year=YEAR)
    on_top = compute_income_tax_reserve(Decimal("30000"), "Germany", year=YEAR, other_income=Decimal("36000"))

    assert on_top.total_annual_reserve > alone.total_annual_reserve
    assert on_top.effective_rate > alone.effective_rate


def test_without_other_income_nothing_changes():
    alone = compute_income_tax_reserve(Decimal("30000"), "Germany", year=YEAR)
    zero = compute_income_tax_reserve(Decimal("30000"), "Germany", year=YEAR, other_income=Decimal(0))

    assert zero == alone


def test_effective_rate_is_the_reserve_over_the_freelance_income():
    reserve = compute_income_tax_reserve(Decimal("30000"), "Germany", year=YEAR, other_income=Decimal("36000"))

    assert reserve.effective_rate == (reserve.total_annual_reserve / Decimal("30000")).quantize(Decimal("0.0001"))


def test_no_freelance_profit_reserves_nothing():
    """The other income's own tax is withheld or owed anyway: none of it is reserved here."""
    reserve = compute_income_tax_reserve(Decimal(0), "Germany", year=YEAR, other_income=Decimal("36000"))

    assert reserve.total_annual_reserve == 0


def test_surcharge_counts_only_the_extra_too():
    """Well above the Soli exemption, the reserved surcharge is the difference as well."""
    freelance, other = Decimal("80000"), Decimal("90000")
    system = get_tax_system("Germany", datetime.date(YEAR, 7, 1))

    reserve = compute_income_tax_reserve(freelance, "Germany", year=YEAR, other_income=other)

    soli_both = system.solidarity_surcharge(system.income_tax(freelance + other))
    soli_other = system.solidarity_surcharge(system.income_tax(other))
    assert reserve.solidarity_surcharge == soli_both - soli_other


# ── Annualising ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "amount, period",
    [("3000", Cycle.monthly), ("9000", Cycle.quarterly), ("36000", Cycle.yearly)],
)
def test_other_income_counts_a_whole_year(amount, period):
    assert annual_other_income([_job(amount, period)], "EUR") == Decimal("36000.00")


def test_other_incomes_add_up():
    incomes = [_job("2000"), _job("6000", Cycle.yearly, title="Rent")]

    assert annual_other_income(incomes, "EUR") == Decimal("30000.00")


# ── Not business revenue ─────────────────────────────────────


def _invoices():
    return [_make_invoice(datetime.date(YEAR, 1, 15), [(100, Decimal("100"), Decimal("0.19"))])]


def test_spendable_income_keeps_other_income_out_of_revenue():
    expenses = [
        RecurringExpense(title="Software", amount=Decimal("50"), currency="EUR", period=Cycle.monthly, tax_deductible=True)
    ]
    alone = compute_spendable_income(_invoices(), "Germany", expenses=expenses, currency="EUR", year=YEAR)
    with_job = compute_spendable_income(
        _invoices(), "Germany", expenses=expenses, currency="EUR", year=YEAR, other_incomes=[_job()]
    )

    assert with_job.net_revenue_ytd == alone.net_revenue_ytd
    assert with_job.taxable_profit == alone.taxable_profit
    assert with_job.tax_base == alone.tax_base
    assert with_job.other_income == Decimal("36000.00")
    assert with_job.income_tax_reserve > alone.income_tax_reserve
    assert with_job.spendable == alone.spendable - (with_job.income_tax_reserve - alone.income_tax_reserve)


def test_spendable_income_reserves_tax_at_the_combined_rate():
    spending = compute_spendable_income(_invoices(), "Germany", currency="EUR", year=YEAR, other_incomes=[_job()])

    expected = compute_income_tax_reserve(
        spending.tax_base, "Germany", year=YEAR, currency="EUR", other_income=Decimal("36000")
    )
    assert spending.income_tax_reserve == expected.ytd_reserve


def test_effective_salary_reserves_more_tax_with_other_income():
    last_month = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
    invoices = [_make_invoice(last_month, [(40, Decimal("100"), Decimal("0.19"))])]
    for inv in invoices:
        inv.paid = True

    alone = compute_effective_salary(invoices, [], "Germany", currency="EUR")
    with_job = compute_effective_salary(invoices, [], "Germany", currency="EUR", other_incomes=[_job()])

    assert with_job.gross_monthly == alone.gross_monthly
    assert with_job.income_tax_reserve_monthly > alone.income_tax_reserve_monthly
    assert with_job.optimistic_monthly < alone.optimistic_monthly


# ── Currencies ───────────────────────────────────────────────


def test_foreign_other_income_is_converted():
    # The suite's stub rate is 0.9 per unit.
    assert annual_other_income([_job("1000", currency="USD")], "EUR") == Decimal("10800.00")


def test_other_income_without_a_rate_is_left_out_and_named(monkeypatch):
    monkeypatch.setattr("tuttle.tax_reserves.convert", lambda *args: None)
    left_out: list = []

    assert annual_other_income([_job(currency="USD")], "EUR", left_out) == 0
    assert left_out == ["Other income Part-time job (USD)"]
