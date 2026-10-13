"""The effective salary: a steady monthly run rate, broken down row by row.

It averages the last 12 complete months, or the months since the first invoice.
"""

import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from tuttle import tax_reserves
from tuttle.model import RecurringExpense
from tuttle.tax_reserves import compute_effective_salary, compute_spendable_income
from tuttle.time import Cycle

from .test_tax import _make_invoice


@pytest.fixture
def today(monkeypatch):
    """Pin the date tax_reserves sees as today."""

    def pin(day: datetime.date):
        class _Date(datetime.date):
            @classmethod
            def today(cls):
                return day

        monkeypatch.setattr(
            tax_reserves,
            "datetime",
            SimpleNamespace(date=_Date, datetime=datetime.datetime, timedelta=datetime.timedelta),
        )

    return pin


def _month_end(year: int, month: int) -> datetime.date:
    return datetime.date(year + month // 12, month % 12 + 1, 1) - datetime.timedelta(days=1)


def _monthly_invoices(year: int, months, net=10000, paid=True):
    invoices = [_make_invoice(_month_end(year, m), [(1, net, 0.19)], vat_rate=0.19) for m in months]
    for inv in invoices:
        inv.paid = paid
    return invoices


def _fixed(amount, deductible=True):
    return RecurringExpense(
        title="Office",
        amount=Decimal(amount),
        currency="EUR",
        period=Cycle.monthly,
        tax_deductible=deductible,
    )


@pytest.mark.parametrize("country", ["Germany", "Spain", "Sweden", "United States"])
def test_steady_income_gives_the_same_salary_all_year(today, country):
    """Progressive tax on a few months' income must not read as a lower tax rate."""
    salaries = set()
    for month in (1, 4, 9, 12):
        today(_month_end(2026, month))
        salary = compute_effective_salary(_monthly_invoices(2026, range(1, month + 1)), [], country, currency="EUR")
        salaries.add(salary.optimistic_monthly)
    assert len(salaries) == 1


def test_a_full_year_matches_safe_to_spend(today):
    """On New Year's Day the salary averages exactly the year just closed."""
    today(datetime.date(2027, 1, 1))
    invoices = _monthly_invoices(2026, range(1, 13))
    expenses = [_fixed("800"), _fixed("200", deductible=False)]

    salary = compute_effective_salary(invoices, expenses, "Germany")
    spending = compute_spendable_income(invoices, "Germany", expenses=expenses, year=2026)

    assert abs(salary.optimistic_monthly * 12 - spending.spendable) < 1


def test_breakdown_adds_up_to_the_optimistic_salary(today):
    today(datetime.date(2026, 10, 31))
    invoices = _monthly_invoices(2026, range(1, 9)) + _monthly_invoices(2026, [9, 10], paid=False)
    health = RecurringExpense(
        title="Health", amount=Decimal(0), currency="EUR", period=Cycle.monthly, rate=Decimal("14.6"), tax_deductible=True
    )
    salary = compute_effective_salary(invoices, [_fixed("1000"), _fixed("300", deductible=False), health], "Germany")

    assert salary.conservative_monthly < salary.optimistic_monthly
    assert salary.gross_monthly == Decimal("11900.00")  # all ten invoices, over ten months
    rows = (
        salary.gross_monthly
        - salary.vat_reserve_monthly
        - salary.income_tax_reserve_monthly
        - salary.monthly_expenses
        - sum(line.amount for line in salary.dynamic_expenses)
        - salary.conversion_fee_monthly
    )
    assert rows == salary.optimistic_monthly


def test_only_deductible_fixed_expenses_lower_the_tax(today):
    today(datetime.date(2026, 10, 31))
    invoices = _monthly_invoices(2026, range(1, 11))
    plain = compute_effective_salary(invoices, [], "Germany")
    deductible = compute_effective_salary(invoices, [_fixed("1000")], "Germany")
    from_taxed_income = compute_effective_salary(invoices, [_fixed("1000", deductible=False)], "Germany")

    assert deductible.income_tax_reserve_monthly < plain.income_tax_reserve_monthly
    assert from_taxed_income.income_tax_reserve_monthly == plain.income_tax_reserve_monthly
    assert from_taxed_income.optimistic_monthly == plain.optimistic_monthly - 1000
    assert from_taxed_income.optimistic_monthly < deductible.optimistic_monthly


@pytest.mark.parametrize("day", [datetime.date(2026, 10, 1), datetime.date(2026, 10, 30), datetime.date(2026, 11, 1)])
def test_the_month_in_progress_does_not_lower_the_salary(today, day):
    """Invoiced at month end: until then the new month has no invoice yet."""
    today(datetime.date(2026, 9, 30))
    steady = compute_effective_salary(_monthly_invoices(2026, range(1, 9)), [], "Germany")

    today(day)
    salary = compute_effective_salary(_monthly_invoices(2026, range(1, day.month)), [], "Germany")
    assert salary.optimistic_monthly == steady.optimistic_monthly


def test_a_business_started_mid_year_averages_its_own_months(today):
    today(datetime.date(2026, 10, 15))
    salary = compute_effective_salary(_monthly_invoices(2026, range(7, 10)), [], "Germany")

    assert salary.gross_monthly == Decimal("11900.00")
    assert (salary.period_start, salary.period_end) == (datetime.date(2026, 7, 1), datetime.date(2026, 9, 30))


def test_january_carries_on_from_last_year(today):
    today(datetime.date(2025, 12, 31))
    december = compute_effective_salary(_monthly_invoices(2025, range(1, 13)), [], "Germany")
    today(datetime.date(2026, 1, 20))
    january = compute_effective_salary(_monthly_invoices(2025, range(1, 13)), [], "Germany")

    # The same monthly revenue; only the year's tax tables differ.
    assert january.gross_monthly == december.gross_monthly == Decimal("11900.00")
    assert january.period_start == datetime.date(2025, 1, 1)


def test_future_invoices_do_not_count(today):
    today(datetime.date(2026, 10, 31))
    invoices = _monthly_invoices(2026, range(1, 11))
    later = _monthly_invoices(2026, [11], paid=False) + _monthly_invoices(2027, [2], paid=False)

    assert compute_effective_salary(invoices + later, [], "Germany") == compute_effective_salary(invoices, [], "Germany")
