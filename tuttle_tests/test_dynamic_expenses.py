"""Tests for income-dependent (dynamic) recurring expenses.

A dynamic expense is a percentage of income rather than a fixed amount, used for
health insurance and pension contributions. Where the percentage bites depends on
whether the expense is tax deductible:

    Net Revenue - Fixed Expenses
    = Taxable Profit                <- rate x this, for deductible expenses
    - Dynamic (deductible)
    = Tax Base -> Est. Income Tax
    = Post-tax                      <- rate x this, for non-deductible expenses
    - Dynamic (non-deductible)
    = Safe to Spend
"""

import datetime
from decimal import Decimal

import pytest

from tuttle.model import RecurringExpense
from tuttle.tax_reserves import compute_effective_salary, compute_spendable_income, dynamic_monthly
from tuttle.time import Cycle

from .test_tax import _make_invoice


def _health(rate="19.6", deductible=True, **kwargs):
    return RecurringExpense(
        title="Health Insurance",
        amount=Decimal(0),
        currency="EUR",
        period=Cycle.monthly,
        category="health",
        rate=Decimal(rate),
        tax_deductible=deductible,
        **kwargs,
    )


@pytest.fixture
def invoices():
    """One paid invoice this month, well clear of the German basic allowance."""
    today = datetime.date.today()
    return [_make_invoice(today.replace(day=1), [(1000, 100, 0.19)])]


class TestDynamicMonthly:
    def test_rate_applies_to_the_income(self):
        assert dynamic_monthly(_health(), Decimal("1000")) == Decimal("196.00")

    def test_max_monthly_caps_the_amount(self):
        expense = _health(max_monthly=Decimal("500"))
        assert dynamic_monthly(expense, Decimal("10000")) == Decimal("500.00")

    def test_min_monthly_is_owed_in_a_bad_year(self):
        expense = _health(min_monthly=Decimal("200"))
        assert dynamic_monthly(expense, Decimal("100")) == Decimal("200.00")
        assert dynamic_monthly(expense, Decimal("-5000")) == Decimal("200.00")

    def test_negative_income_without_a_floor_owes_nothing(self):
        assert dynamic_monthly(_health(), Decimal("-5000")) == Decimal(0)


class TestSpendableIncome:
    def test_deductible_expense_shrinks_the_tax_base(self, invoices):
        plain = compute_spendable_income(invoices, "Germany")
        dynamic = compute_spendable_income(invoices, "Germany", expenses=[_health()])

        assert dynamic.taxable_profit == plain.taxable_profit
        assert dynamic.dynamic_expenses_deductible > 0
        assert dynamic.dynamic_expenses_post_tax == 0
        assert dynamic.tax_base == dynamic.taxable_profit - dynamic.dynamic_expenses_deductible
        assert dynamic.income_tax_reserve < plain.income_tax_reserve
        assert dynamic.spendable == dynamic.tax_base - dynamic.income_tax_reserve

    def test_non_deductible_expense_is_charged_on_post_tax_money(self, invoices):
        plain = compute_spendable_income(invoices, "Germany")
        dynamic = compute_spendable_income(invoices, "Germany", expenses=[_health(deductible=False)])

        # The tax bill is untouched; the contribution comes out of what is left.
        assert dynamic.tax_base == dynamic.taxable_profit == plain.taxable_profit
        assert dynamic.income_tax_reserve == plain.income_tax_reserve
        assert dynamic.dynamic_expenses_deductible == 0

        post_tax = dynamic.taxable_profit - dynamic.income_tax_reserve
        expected = post_tax * Decimal("0.196")
        assert abs(dynamic.dynamic_expenses_post_tax - expected) < 1  # per-month rounding
        assert dynamic.spendable == post_tax - dynamic.dynamic_expenses_post_tax

    def test_deductible_costs_less_than_non_deductible(self, invoices):
        deductible = compute_spendable_income(invoices, "Germany", expenses=[_health()])
        taxed = compute_spendable_income(invoices, "Germany", expenses=[_health(deductible=False)])
        assert deductible.spendable > taxed.spendable

    def test_no_rate_means_the_expense_stays_fixed(self, invoices):
        fixed = RecurringExpense(
            title="Health Insurance",
            amount=Decimal("350"),
            currency="EUR",
            period=Cycle.monthly,
            category="health",
            tax_deductible=True,
        )
        result = compute_spendable_income(invoices, "Germany", expenses=[fixed])
        assert result.business_expenses > 0
        assert result.dynamic_expenses_deductible == 0
        assert result.dynamic_expenses_post_tax == 0
        assert result.tax_base == result.taxable_profit

    def test_planned_revenue_is_excluded_from_the_rate_base(self, invoices):
        """Planned calendar revenue is taxed but does not raise the contribution."""
        from unittest.mock import patch

        expenses = [_health()]
        with patch("tuttle.tax_reserves.compute_planned_revenue", return_value=Decimal("50000")):
            import pandas

            with_planned = compute_spendable_income(
                invoices,
                "Germany",
                expenses=expenses,
                projects=["stand-in for a project, compute_planned_revenue is patched"],
                time_data=pandas.DataFrame({"x": [1]}),
            )
        without_planned = compute_spendable_income(invoices, "Germany", expenses=expenses)

        assert with_planned.planned_revenue == Decimal("50000")
        assert with_planned.taxable_profit > without_planned.taxable_profit
        # Same contribution despite the far larger taxable profit.
        assert with_planned.dynamic_expenses_deductible == without_planned.dynamic_expenses_deductible

    def test_cap_limits_a_strong_year(self, invoices):
        uncapped = compute_spendable_income(invoices, "Germany", expenses=[_health()])
        capped = compute_spendable_income(invoices, "Germany", expenses=[_health(max_monthly=Decimal("50"))])
        assert capped.dynamic_expenses_deductible < uncapped.dynamic_expenses_deductible
        assert capped.spendable > uncapped.spendable


class TestBreakdown:
    """Each dynamic expense is listed on its own, not lumped into one total."""

    def test_one_line_per_expense(self, invoices):
        pension = _health(rate="9.3", deductible=False)
        pension.title = "Pension Plan"
        pension.category = "pension"
        result = compute_spendable_income(invoices, "Germany", expenses=[_health(), pension])

        titles = [line.title for line in result.dynamic_expenses]
        assert titles == ["Health Insurance", "Pension Plan"]
        assert [line.tax_deductible for line in result.dynamic_expenses] == [True, False]
        assert [line.rate for line in result.dynamic_expenses] == [Decimal("19.6"), Decimal("9.3")]

        deductible = [line for line in result.dynamic_expenses if line.tax_deductible]
        assert sum(line.amount for line in deductible) == result.dynamic_expenses_deductible
        post_tax = [line for line in result.dynamic_expenses if not line.tax_deductible]
        assert sum(line.amount for line in post_tax) == result.dynamic_expenses_post_tax

    def test_fixed_expenses_are_not_listed(self, invoices):
        fixed = RecurringExpense(title="Software", amount=Decimal("100"), currency="EUR", period=Cycle.monthly)
        result = compute_spendable_income(invoices, "Germany", expenses=[fixed])
        assert result.dynamic_expenses == []

    def test_effective_salary_lists_each_expense(self, invoices):
        pension = _health(rate="9.3")
        pension.title = "Pension Plan"
        salary = compute_effective_salary(invoices, [_health(), pension], "Germany")

        assert [line.title for line in salary.dynamic_expenses] == ["Health Insurance", "Pension Plan"]
        assert all(line.amount > 0 for line in salary.dynamic_expenses)


class TestEffectiveSalary:
    def test_dynamic_expense_lowers_the_salary(self, invoices):
        plain = compute_effective_salary(invoices, [], "Germany")
        dynamic = compute_effective_salary(invoices, [_health()], "Germany")

        assert plain.dynamic_expenses == []
        assert sum(line.amount for line in dynamic.dynamic_expenses) > 0
        assert dynamic.conservative_monthly < plain.conservative_monthly
        assert dynamic.optimistic_monthly < plain.optimistic_monthly

    def test_fixed_expenses_are_unchanged(self, invoices):
        fixed = RecurringExpense(title="Software", amount=Decimal("100"), currency="EUR", period=Cycle.monthly)
        result = compute_effective_salary(invoices, [fixed], "Germany")
        assert result.monthly_expenses == Decimal("100.00")
        assert result.dynamic_expenses == []
