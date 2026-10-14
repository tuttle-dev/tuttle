"""Tax reserve calculations for freelancers.

Computes how much of the freelancer's revenue must be set aside for
VAT payments and estimated income tax, yielding the actual spendable income.
"""

import calendar
import datetime
import logging
from decimal import Decimal
from typing import List, NamedTuple, Optional

from pandas import DataFrame

from .fx import convert, fx_haircut
from .fx import rate as fx_rate
from .model import Invoice, Project, RecurringExpense
from .tax import get_tax_system
from .time import Cycle, TimeUnit
from .timetracking import drop_invoiced, sum_hours_by_tag

logger = logging.getLogger(__name__)


class VATReserve(NamedTuple):
    """VAT collected that must be remitted to the tax authority."""

    vat_collected: Decimal  # total VAT on invoices in the period
    invoice_count: int  # number of invoices considered
    period_start: datetime.date
    period_end: datetime.date


class IncomeTaxReserve(NamedTuple):
    """Estimated income tax reserve based on known income."""

    estimated_annual_tax: Decimal
    solidarity_surcharge: Decimal
    total_annual_reserve: Decimal  # tax + soli
    ytd_reserve: Decimal  # equals total_annual_reserve (no proration)
    effective_rate: Decimal  # total_annual_reserve / income


class DynamicExpenseLine(NamedTuple):
    """One income-dependent expense, resolved to an amount for the period."""

    title: str
    rate: Decimal  # percentage of the income it is charged on
    amount: Decimal
    tax_deductible: bool


class SpendableIncome(NamedTuple):
    """What the freelancer can actually spend."""

    gross_revenue_ytd: Decimal  # total invoiced amount (incl. VAT)
    business_expenses: Decimal  # tax-deductible fixed recurring expenses prorated to period
    net_revenue_ytd: Decimal  # gross minus VAT
    taxable_profit: Decimal  # net_revenue - business_expenses
    vat_reserve: Decimal  # VAT to set aside
    income_tax_reserve: Decimal  # estimated income tax + soli
    spendable: Decimal  # post-tax minus non-deductible expenses and FX fee
    # breakdown by income source
    received_gross: Decimal  # paid invoices, gross
    received_net: Decimal  # paid invoices, net of VAT
    outstanding_gross: Decimal  # sent but unpaid, gross
    outstanding_net: Decimal  # sent but unpaid, net of VAT
    planned_revenue: Decimal  # calendar work this year not yet invoiced (net)
    contracted_revenue: Decimal = Decimal(0)  # committed contract work not yet in the calendar (net)
    conversion_fee: Decimal = Decimal(0)  # FX spread on foreign-currency revenue
    # income-dependent (dynamic) expenses, split by where they land in the waterfall
    dynamic_expenses_deductible: Decimal = Decimal(0)  # charged on the taxable profit
    dynamic_expenses_post_tax: Decimal = Decimal(0)  # charged on post-tax money
    tax_base: Decimal = Decimal(0)  # taxable_profit - dynamic_expenses_deductible
    dynamic_expenses: list = []  # per-expense DynamicExpenseLine, never mutated
    fixed_expenses_post_tax: Decimal = Decimal(0)  # non-deductible fixed expenses prorated to period


def _invoice_currency(inv: Invoice) -> Optional[str]:
    """Return the ISO 4217 currency code for an invoice, or None."""
    if inv.contract and inv.contract.currency:
        return inv.contract.currency
    return None


def _revenue_amounts(inv: Invoice) -> tuple[Decimal, Decimal]:
    """The (total, VAT) an invoice adds to revenue, in its own currency.

    A reminder repeats the items of the invoice it chases, so it adds nothing.
    A final invoice states the whole contract price and deducts the deposits,
    which count on their own, so it adds only the remainder.
    """
    if inv.is_reminder:
        return Decimal(0), Decimal(0)
    deducted = inv.deposit_deductions
    total = inv.total - sum((d["gross"] for d in deducted), Decimal(0))
    vat = inv.VAT_total - sum((d["vat"] for d in deducted), Decimal(0))
    return total, vat


def convert_invoice(inv: Invoice, currency: Optional[str]) -> Optional[tuple[Decimal, Decimal]]:
    """The (total, VAT) an invoice adds to revenue, expressed in *currency*.

    Returns ``None`` when the invoice is in another currency and the ECB rate
    for its month cannot be resolved — the caller must leave it out and say so,
    never count it as zero.
    """
    total, vat = _revenue_amounts(inv)
    inv_currency = _invoice_currency(inv)
    if not currency or inv_currency in (currency, None):
        return total, vat

    if vat:
        # The design's third row: place of supply is domestic, so the invoice
        # carries VAT in a foreign currency. Converting it needs rounding rules
        # we deliberately do not have — warn instead of guessing.
        logger.warning(
            "Invoice %s is in %s and carries VAT (%s). VAT on foreign-currency "
            "invoices is not supported; the converted VAT figure is an estimate.",
            inv.number or inv.id,
            inv_currency,
            vat,
        )

    converted_total = convert(total, inv_currency, currency, inv.date)
    converted_vat = convert(vat, inv_currency, currency, inv.date)
    if converted_total is None or converted_vat is None:
        return None
    return converted_total, converted_vat


def compute_planned_revenue(
    projects: List[Project],
    time_data: Optional[DataFrame] = None,
    currency: Optional[str] = None,
    invoices: Optional[List[Invoice]] = None,
) -> Decimal:
    """Net revenue from this year's calendar work, past and future, not yet invoiced.

    Hours in a timesheet of a non-cancelled invoice are left out. Converts
    hours to revenue via each project's contract rate, and contracts in a
    foreign currency into *currency* at the current month's rate (uninvoiced
    work has no invoice date to pin a rate to).
    """
    if time_data is None or time_data.empty:
        return Decimal(0)

    today = datetime.date.today()
    year_start = datetime.date(today.year, 1, 1)
    year_end = datetime.date(today.year, 12, 31)

    tag_to_project = {p.tag: p for p in projects if p.tag and p.contract}

    if not tag_to_project:
        return Decimal(0)

    tag_to_workday = {tag: p.contract.units_per_workday for tag, p in tag_to_project.items()}

    idx_dates = time_data.index.date
    mask = (idx_dates >= year_start) & (idx_dates <= year_end)
    planned = drop_invoiced(time_data[mask], invoices or [])
    if planned.empty:
        return Decimal(0)

    planned_by_tag = sum_hours_by_tag(planned, tag_to_workday)

    total = Decimal(0)
    for tag, hours in planned_by_tag.items():
        project = tag_to_project.get(tag)
        if not project:
            continue
        contract = project.contract
        if not contract.rate:
            continue
        unit_hours = contract.units_per_workday if contract.unit == TimeUnit.day else 1
        billable_units = Decimal(str(hours)) / Decimal(str(unit_hours))
        revenue = billable_units * contract.rate
        if currency and contract.currency not in (currency, None):
            converted = convert(revenue, contract.currency, currency, today)
            if converted is None:
                continue
            revenue = converted
        total += revenue

    return total.quantize(Decimal("0.01"))


def compute_vat_reserves(
    invoices: List[Invoice],
    period_start: datetime.date,
    period_end: datetime.date,
    currency: Optional[str] = None,
) -> VATReserve:
    """Sum VAT collected on non-cancelled invoices in the given period.

    Invoices in another currency are converted to *currency* at the ECB monthly
    average. For the supported cases (reverse charge, outside scope) their VAT
    is zero before and after conversion. Reminders collect no VAT of their own.
    """
    vat_total = Decimal(0)
    count = 0
    for inv in invoices:
        if inv.cancelled or inv.is_reminder:
            continue
        if period_start <= inv.date <= period_end:
            converted = convert_invoice(inv, currency)
            if converted is None:
                continue
            vat_total += converted[1]
            count += 1
    return VATReserve(
        vat_collected=vat_total,
        invoice_count=count,
        period_start=period_start,
        period_end=period_end,
    )


def compute_income_tax_reserve(
    income: Decimal,
    country: str,
    deductions: Decimal = Decimal(0),
    year: Optional[int] = None,
    currency: Optional[str] = None,
) -> IncomeTaxReserve:
    """Estimate income tax reserve based on total known income.

    *income* is the total expected net income (received + invoiced + planned).
    Tax is computed directly on this amount — no annualization.

    *income* and the returned amounts are in *currency* (default: the tax
    system's). The tariff is written in the tax system's currency, so income
    in another one is converted for it, and the tax back.
    """
    today = datetime.date.today()
    _zero = IncomeTaxReserve(
        estimated_annual_tax=Decimal(0),
        solidarity_surcharge=Decimal(0),
        total_annual_reserve=Decimal(0),
        ytd_reserve=Decimal(0),
        effective_rate=Decimal(0),
    )

    ref_date = datetime.date(year, 7, 1) if year is not None else today

    try:
        tax_system = get_tax_system(country, date=ref_date)
    except NotImplementedError:
        return _zero

    taxable_income = income - deductions
    if taxable_income <= 0:
        return _zero

    to_tax_currency = Decimal(1)
    if currency and currency != tax_system.currency:
        to_tax_currency = fx_rate(currency, tax_system.currency, ref_date)
        if to_tax_currency is None:
            logger.warning(
                "No %s/%s rate; estimating %s tax on the %s amount as is.",
                currency,
                tax_system.currency,
                tax_system.country,
                currency,
            )
            to_tax_currency = Decimal(1)

    annual_tax = tax_system.income_tax(taxable_income * to_tax_currency) / to_tax_currency
    annual_soli = tax_system.solidarity_surcharge(annual_tax * to_tax_currency) / to_tax_currency
    total_annual = annual_tax + annual_soli
    reserve = total_annual.quantize(Decimal("0.01"))

    effective_rate = (total_annual / taxable_income) if taxable_income > 0 else Decimal(0)

    return IncomeTaxReserve(
        estimated_annual_tax=annual_tax,
        solidarity_surcharge=annual_soli,
        total_annual_reserve=total_annual,
        ytd_reserve=reserve,
        effective_rate=effective_rate.quantize(Decimal("0.0001")),
    )


def compute_spendable_income(
    invoices: List[Invoice],
    country: str,
    expenses: Optional[List[RecurringExpense]] = None,
    deductions: Decimal = Decimal(0),
    currency: Optional[str] = None,
    year: Optional[int] = None,
    projects: Optional[List[Project]] = None,
    time_data: Optional[DataFrame] = None,
    contracted: Decimal = Decimal(0),
) -> SpendableIncome:
    """Compute spendable income: what's left after VAT, expenses, and income tax.

    This answers the freelancer's core question: "How much of this money is mine?"

    Income basis = received (paid) + outstanding (invoiced) + planned (calendar)
    + contracted (committed contract work for the rest of the year).
    Fixed expenses marked tax deductible (operating costs, insurance, etc.) are
    deducted before estimating income tax, yielding the taxable profit; the
    others are paid out of taxed income.
    Tax is computed on the taxable profit — no annualization.

        Gross Revenue
        − VAT
        = Net Revenue (received + outstanding) + Planned + Contracted
        − Deductible Fixed Expenses
        = Taxable Profit
        − Est. Income Tax
        − Other Fixed Expenses
        = Safe to Spend

    If *projects* and *time_data* are given, planned revenue from this year's
    calendar work that no invoice covers yet is included in the income basis.
    *contracted* is net revenue still expected from committed contracts this
    year, as computed by ``forecasting.contracted_revenue``; other years
    ignore it.
    """
    today = datetime.date.today()
    # Any year but the current one is a whole year, without planned revenue.
    other_year = year is not None and year != today.year

    if other_year:
        year_start = datetime.date(year, 1, 1)
        year_end = datetime.date(year, 12, 31)
    else:
        year_start = today.replace(month=1, day=1)
        year_end = today

    ref_date = datetime.date(year, 7, 1) if year is not None else today

    if currency is None:
        try:
            tax_system = get_tax_system(country, date=ref_date)
            currency = tax_system.currency
        except NotImplementedError:
            pass

    received_gross = Decimal(0)
    received_vat = Decimal(0)
    outstanding_gross = Decimal(0)
    outstanding_vat = Decimal(0)
    foreign_net = Decimal(0)  # converted net revenue that must be exchanged

    for inv in invoices:
        if inv.cancelled:
            continue
        if year_start <= inv.date <= year_end:
            converted = convert_invoice(inv, currency)
            if converted is None:
                continue
            gross, vat = converted
            if _invoice_currency(inv) not in (currency, None):
                foreign_net += gross - vat
            if inv.paid:
                received_gross += gross
                received_vat += vat
            else:
                outstanding_gross += gross
                outstanding_vat += vat

    received_net = received_gross - received_vat
    outstanding_net = outstanding_gross - outstanding_vat

    planned = Decimal(0)
    if not other_year and projects and time_data is not None:
        planned = compute_planned_revenue(projects, time_data, currency=currency, invoices=invoices)
    if other_year:
        contracted = Decimal(0)

    gross_ytd = received_gross + outstanding_gross
    vat_ytd = received_vat + outstanding_vat
    net_ytd = received_net + outstanding_net

    if other_year:
        months_elapsed = 12
    else:
        months_elapsed = max(
            (today.year - year_start.year) * 12 + today.month - year_start.month + 1,
            1,
        )

    # Prorate the fixed-amount recurring expenses to the period
    fixed_expenses = [e for e in (expenses or []) if e.rate is None]
    dynamic_expenses = [e for e in (expenses or []) if e.rate is not None]
    deductible_monthly = _monthly_expenses_total([e for e in fixed_expenses if e.tax_deductible], currency)
    post_tax_monthly = _monthly_expenses_total([e for e in fixed_expenses if not e.tax_deductible], currency)
    biz_expenses_ytd = (deductible_monthly * months_elapsed).quantize(Decimal("0.01"))
    fixed_post_tax_ytd = (post_tax_monthly * months_elapsed).quantize(Decimal("0.01"))

    taxable_profit = net_ytd + planned + contracted - biz_expenses_ytd

    # Dynamic expenses are charged on income actually earned so far, so planned
    # and contracted revenue stay out of their base even though they are taxed.
    dynamic_base_monthly = (net_ytd - biz_expenses_ytd) / months_elapsed

    deductible_lines = _dynamic_lines(dynamic_expenses, dynamic_base_monthly, deductible=True)
    dyn_deductible = (_lines_total(deductible_lines) * months_elapsed).quantize(Decimal("0.01"))

    # Deductible provisions (health insurance, Rürup) shrink the income the tax
    # is assessed on; the rest is paid out of money that was already taxed.
    tax_base = taxable_profit - dyn_deductible
    tax_reserve = compute_income_tax_reserve(tax_base, country, deductions, year=year, currency=currency)

    post_tax = tax_base - tax_reserve.ytd_reserve - fixed_post_tax_ytd

    # Post-tax dynamic expenses are charged on earned income too: planned
    # revenue, and its share of the tax, stay out of their base.
    earned_base = net_ytd - biz_expenses_ytd - dyn_deductible
    earned_tax = tax_reserve.ytd_reserve * max(earned_base, Decimal(0)) / tax_base if tax_base > 0 else Decimal(0)
    earned_post_tax = earned_base - earned_tax - fixed_post_tax_ytd
    post_tax_lines = _dynamic_lines(dynamic_expenses, earned_post_tax / months_elapsed, deductible=False)
    dyn_post_tax = (_lines_total(post_tax_lines) * months_elapsed).quantize(Decimal("0.01"))

    # The per-expense lines are monthly; the aggregates above cover the period.
    dynamic_lines = [
        line._replace(amount=(line.amount * months_elapsed).quantize(Decimal("0.01")))
        for line in deductible_lines + post_tax_lines
    ]

    # The bank/Wise spread never reduces taxable revenue — only what lands in
    # the account, so it is subtracted after the tax reserve, not before.
    conversion_fee = (foreign_net * fx_haircut() / 100).quantize(Decimal("0.01"))

    spendable = post_tax - dyn_post_tax - conversion_fee

    return SpendableIncome(
        gross_revenue_ytd=gross_ytd,
        business_expenses=biz_expenses_ytd,
        net_revenue_ytd=net_ytd,
        taxable_profit=taxable_profit,
        vat_reserve=vat_ytd,
        income_tax_reserve=tax_reserve.ytd_reserve,
        spendable=spendable,
        received_gross=received_gross,
        received_net=received_net,
        outstanding_gross=outstanding_gross,
        outstanding_net=outstanding_net,
        planned_revenue=planned,
        contracted_revenue=contracted,
        conversion_fee=conversion_fee,
        dynamic_expenses_deductible=dyn_deductible,
        dynamic_expenses_post_tax=dyn_post_tax,
        tax_base=tax_base,
        dynamic_expenses=dynamic_lines,
        fixed_expenses_post_tax=fixed_post_tax_ytd,
    )


# How many months one period spans.
PERIOD_TO_MONTHS = {
    Cycle.monthly: Decimal(1),
    Cycle.quarterly: Decimal(3),
    Cycle.yearly: Decimal(12),
    Cycle.weekly: Decimal(12) / 52,
    Cycle.daily: Decimal(12) / 365,
    Cycle.hourly: Decimal(1) / 160,  # rough ~160 work-hours/month
}


def dynamic_monthly(expense: RecurringExpense, monthly_income: Decimal) -> Decimal:
    """Monthly amount of a dynamic expense, charged on a bounded income base.

    The bounds work like a Beitragsbemessungsgrundlage: they clamp the *income*
    the rate is charged on, not the resulting contribution. A ceiling of 70,000
    a year means income above that is free of the contribution, so the expense
    tops out at 70,000 × rate — and a floor is a minimum assumed income, which
    is what keeps a contribution owed in a loss-making year.

    The bounds are entered on the basis the expense's ``period`` names, so they
    are divided down to a monthly figure first. Clamping monthly is the same as
    clamping the year and dividing, and it keeps a part-year view pro-rata.
    """
    divisor = PERIOD_TO_MONTHS.get(expense.period, Decimal(1))
    base = monthly_income
    if expense.min_base is not None:
        base = max(base, expense.min_base / divisor)
    if expense.max_base is not None:
        base = min(base, expense.max_base / divisor)
    return max(base * expense.rate / 100, Decimal(0)).quantize(Decimal("0.01"))


def _dynamic_lines(
    expenses: List[RecurringExpense],
    monthly_income: Decimal,
    deductible: bool,
) -> List[DynamicExpenseLine]:
    """Monthly amount of each dynamic expense matching *deductible*."""
    return [
        DynamicExpenseLine(
            title=e.title,
            rate=e.rate,
            amount=dynamic_monthly(e, monthly_income),
            tax_deductible=bool(e.tax_deductible),
        )
        for e in expenses
        if bool(e.tax_deductible) is deductible
    ]


def _lines_total(lines: List[DynamicExpenseLine]) -> Decimal:
    return sum((line.amount for line in lines), Decimal(0))


def _normalize_to_monthly(expense: RecurringExpense, currency: Optional[str] = None) -> Optional[Decimal]:
    """A recurring expense's monthly equivalent, in *currency* at this month's rate.

    Returns ``None`` when the expense is in another currency and the rate
    cannot be resolved.
    """
    monthly = expense.amount / PERIOD_TO_MONTHS.get(expense.period, Decimal(1))
    if currency and expense.currency not in (currency, None):
        monthly = convert(monthly, expense.currency, currency, datetime.date.today())
        if monthly is None:
            return None
    return monthly.quantize(Decimal("0.01"))


def _monthly_expenses_total(expenses: List[RecurringExpense], currency: Optional[str] = None) -> Decimal:
    """Sum recurring expenses as monthly amounts in *currency*.

    An expense whose exchange rate cannot be resolved is left out, as an
    invoice is; fx logs which.
    """
    amounts = (_normalize_to_monthly(e, currency) for e in expenses)
    return sum((a for a in amounts if a is not None), Decimal(0))


class EffectiveSalary(NamedTuple):
    """The freelancer's safe-to-spend monthly salary, expressed as a range.

    conservative_monthly — floor: based only on revenue already received (paid invoices)
    optimistic_monthly   — ceiling: includes outstanding (unpaid, non-cancelled) invoices

    The remaining fields break down the optimistic figure, so that
    gross − VAT − tax − fixed − dynamic − conversion fee = optimistic_monthly:

    gross_monthly        — monthly gross revenue (incl. VAT)
    vat_reserve_monthly        — VAT to remit per month
    income_tax_reserve_monthly — income-tax reserve per month
    monthly_expenses     — normalized total of the fixed recurring expenses
    dynamic_expenses     — income-dependent expenses (health, pension), one line each
    conversion_fee_monthly — bank spread on foreign-currency revenue per month
    currency             — ISO 4217 currency code
    period_start, period_end — the months the averages are taken over
    """

    conservative_monthly: Decimal
    optimistic_monthly: Decimal
    monthly_expenses: Decimal
    income_tax_reserve_monthly: Decimal
    vat_reserve_monthly: Decimal
    currency: str
    dynamic_expenses: list = []  # per-expense DynamicExpenseLine, never mutated
    gross_monthly: Decimal = Decimal(0)
    conversion_fee_monthly: Decimal = Decimal(0)
    period_start: Optional[datetime.date] = None
    period_end: Optional[datetime.date] = None


class _Revenue(NamedTuple):
    """Year-to-date revenue of one scenario, in the aggregate currency."""

    gross: Decimal = Decimal(0)
    vat: Decimal = Decimal(0)
    foreign_net: Decimal = Decimal(0)  # net revenue that must be exchanged

    def __add__(self, other: "_Revenue") -> "_Revenue":
        return _Revenue(self.gross + other.gross, self.vat + other.vat, self.foreign_net + other.foreign_net)


class _SalaryScenario(NamedTuple):
    salary: Decimal
    gross: Decimal
    vat: Decimal
    income_tax: Decimal
    conversion_fee: Decimal
    dynamic_lines: List[DynamicExpenseLine]


def compute_effective_salary(
    invoices: List[Invoice],
    expenses: List[RecurringExpense],
    country: str,
    currency: Optional[str] = None,
) -> EffectiveSalary:
    """Compute the freelancer's effective monthly salary range.

    The *conservative* figure uses only paid invoices (certain, received revenue).
    The *optimistic* figure adds outstanding (sent but unpaid) invoices.
    Both average the invoices of the last 12 complete months, or of the months
    since the first invoice, and reduce that by VAT, the income-tax reserve,
    the fixed and dynamic recurring expenses, and the bank spread on
    foreign-currency revenue.

    The month in progress is left out: most of its invoices are not written
    yet, so counting it would lower the average every time a month begins.
    """
    today = datetime.date.today()
    this_month = today.replace(day=1)
    cent = Decimal("0.01")

    if currency is None:
        try:
            tax_system = get_tax_system(country, date=today)
            currency = tax_system.currency
        except NotImplementedError:
            currency = "EUR"

    first = min((inv.date for inv in invoices if not inv.cancelled and inv.date <= today), default=None)
    if first is None or first >= this_month:
        # Nothing invoiced before this month: the month so far is all there is.
        period_start, period_end, months = this_month, today, 1
    else:
        period_start = max(this_month.replace(year=this_month.year - 1), first.replace(day=1))
        period_end = this_month - datetime.timedelta(days=1)
        months = (period_end.year - period_start.year) * 12 + period_end.month - period_start.month + 1

    paid = _Revenue()
    outstanding = _Revenue()
    for inv in invoices:
        if inv.cancelled or not period_start <= inv.date <= period_end:
            continue
        converted = convert_invoice(inv, currency)
        if converted is None:
            continue
        gross, vat = converted
        foreign = gross - vat if _invoice_currency(inv) not in (currency, None) else Decimal(0)
        revenue = _Revenue(gross, vat, foreign)
        if inv.paid:
            paid += revenue
        else:
            outstanding += revenue

    fixed_expenses = [e for e in expenses if e.rate is None]
    dynamic_expenses = [e for e in expenses if e.rate is not None]
    monthly_exp = _monthly_expenses_total(fixed_expenses, currency)
    monthly_exp_deductible = _monthly_expenses_total([e for e in fixed_expenses if e.tax_deductible], currency)
    fx_spread = fx_haircut()

    def scenario(revenue: _Revenue) -> _SalaryScenario:
        """The monthly salary waterfall for a year-to-date revenue basis."""
        gross = (revenue.gross / months).quantize(cent)
        vat = (revenue.vat / months).quantize(cent)
        profit = gross - vat - monthly_exp_deductible
        deductible_lines = _dynamic_lines(dynamic_expenses, profit, deductible=True)
        tax_base = profit - _lines_total(deductible_lines)
        # Tax a year of this monthly profit: progressive tax on the year-to-date
        # sum would treat a few months of income as a whole year's.
        income_tax = (compute_income_tax_reserve(tax_base * 12, country, currency=currency).ytd_reserve / 12).quantize(cent)
        post_tax = tax_base - income_tax - (monthly_exp - monthly_exp_deductible)
        post_tax_lines = _dynamic_lines(dynamic_expenses, post_tax, deductible=False)
        # The bank spread never reduces taxable revenue, only what lands in the account.
        conversion_fee = (revenue.foreign_net / months * fx_spread / 100).quantize(cent)
        salary = post_tax - _lines_total(post_tax_lines) - conversion_fee
        return _SalaryScenario(salary, gross, vat, income_tax, conversion_fee, deductible_lines + post_tax_lines)

    conservative = scenario(paid)
    optimistic = scenario(paid + outstanding)

    return EffectiveSalary(
        conservative_monthly=conservative.salary,
        optimistic_monthly=optimistic.salary,
        monthly_expenses=monthly_exp,
        income_tax_reserve_monthly=optimistic.income_tax,
        vat_reserve_monthly=optimistic.vat,
        currency=currency,
        dynamic_expenses=optimistic.dynamic_lines,
        gross_monthly=optimistic.gross,
        conversion_fee_monthly=optimistic.conversion_fee,
        period_start=period_start,
        period_end=period_end,
    )


def monthly_vat_breakdown(
    invoices: List[Invoice],
    year: Optional[int] = None,
    currency: Optional[str] = None,
) -> list:
    """VAT breakdown by month for the given year.

    Returns list of dicts: month, vat_collected, invoice_count, period_start, period_end.
    """
    if year is None:
        year = datetime.date.today().year

    month_names = [calendar.month_abbr[m] for m in range(1, 13)]
    months = []
    for m in range(1, 13):
        period_start = datetime.date(year, m, 1)
        if m == 12:
            period_end = datetime.date(year, 12, 31)
        else:
            period_end = datetime.date(year, m + 1, 1) - datetime.timedelta(days=1)

        reserve = compute_vat_reserves(invoices, period_start, period_end, currency=currency)
        months.append(
            {
                "month": month_names[m - 1],
                "vat_collected": reserve.vat_collected,
                "invoice_count": reserve.invoice_count,
                "period_start": period_start,
                "period_end": period_end,
            }
        )
    return months
