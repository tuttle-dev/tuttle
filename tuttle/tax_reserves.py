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
from .model import Invoice, Project, RecurringExpense
from .tax import get_tax_system
from .time import Cycle, TimeUnit
from .timetracking import sum_hours_by_tag

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
    business_expenses: Decimal  # fixed recurring expenses prorated to period
    net_revenue_ytd: Decimal  # gross minus VAT
    taxable_profit: Decimal  # net_revenue - business_expenses
    vat_reserve: Decimal  # VAT to set aside
    income_tax_reserve: Decimal  # estimated income tax + soli
    spendable: Decimal  # post-tax minus non-deductible dynamic expenses and FX fee
    # breakdown by income source
    received_gross: Decimal  # paid invoices, gross
    received_net: Decimal  # paid invoices, net of VAT
    outstanding_gross: Decimal  # sent but unpaid, gross
    outstanding_net: Decimal  # sent but unpaid, net of VAT
    planned_revenue: Decimal  # calendar-derived future revenue (net)
    conversion_fee: Decimal = Decimal(0)  # FX spread on foreign-currency revenue
    # income-dependent (dynamic) expenses, split by where they land in the waterfall
    dynamic_expenses_deductible: Decimal = Decimal(0)  # charged on the taxable profit
    dynamic_expenses_post_tax: Decimal = Decimal(0)  # charged on post-tax money
    tax_base: Decimal = Decimal(0)  # taxable_profit - dynamic_expenses_deductible
    dynamic_expenses: list = []  # per-expense DynamicExpenseLine, never mutated


def _invoice_currency(inv: Invoice) -> Optional[str]:
    """Return the ISO 4217 currency code for an invoice, or None."""
    if inv.contract and inv.contract.currency:
        return inv.contract.currency
    return None


def convert_invoice(inv: Invoice, currency: Optional[str]) -> Optional[tuple[Decimal, Decimal]]:
    """Invoice (total, VAT) expressed in *currency*.

    Returns ``None`` when the invoice is in another currency and the ECB rate
    for its month cannot be resolved — the caller must leave it out and say so,
    never count it as zero.
    """
    inv_currency = _invoice_currency(inv)
    if not currency or inv_currency in (currency, None):
        return inv.total, inv.VAT_total

    if inv.VAT_total:
        # The design's third row: place of supply is domestic, so the invoice
        # carries VAT in a foreign currency. Converting it needs rounding rules
        # we deliberately do not have — warn instead of guessing.
        logger.warning(
            "Invoice %s is in %s and carries VAT (%s). VAT on foreign-currency "
            "invoices is not supported; the converted VAT figure is an estimate.",
            inv.number or inv.id,
            inv_currency,
            inv.VAT_total,
        )

    total = convert(inv.total, inv_currency, currency, inv.date)
    vat = convert(inv.VAT_total, inv_currency, currency, inv.date)
    if total is None or vat is None:
        return None
    return total, vat


def compute_planned_revenue(
    projects: List[Project],
    time_data: Optional[DataFrame] = None,
    currency: Optional[str] = None,
) -> Decimal:
    """Net revenue expected from future calendar events in the current year.

    Converts planned hours to revenue via each project's contract rate, and
    contracts in a foreign currency into *currency* at the current month's rate
    (future revenue has no invoice date to pin a rate to).
    """
    if time_data is None or time_data.empty:
        return Decimal(0)

    today = datetime.date.today()
    year_end = datetime.date(today.year, 12, 31)

    tag_to_project = {p.tag: p for p in projects if p.tag and p.contract}

    if not tag_to_project:
        return Decimal(0)

    tag_to_workday = {tag: p.contract.units_per_workday for tag, p in tag_to_project.items()}

    idx_dates = time_data.index.date
    mask = (idx_dates >= today) & (idx_dates <= year_end)
    future = time_data[mask]
    if future.empty:
        return Decimal(0)

    planned_by_tag = sum_hours_by_tag(future, tag_to_workday)

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
    is zero before and after conversion.
    """
    vat_total = Decimal(0)
    count = 0
    for inv in invoices:
        if inv.cancelled:
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
) -> IncomeTaxReserve:
    """Estimate income tax reserve based on total known income.

    *income* is the total expected net income (received + invoiced + planned).
    Tax is computed directly on this amount — no annualization.
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

    annual_tax = tax_system.income_tax(taxable_income)
    annual_soli = tax_system.solidarity_surcharge(annual_tax)
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
) -> SpendableIncome:
    """Compute spendable income: what's left after VAT, expenses, and income tax.

    This answers the freelancer's core question: "How much of this money is mine?"

    Income basis = received (paid) + outstanding (invoiced) + planned (calendar).
    Business *expenses* (health insurance, operating costs, etc.) are deducted
    before estimating income tax, yielding the correct taxable profit.
    Tax is computed on the taxable profit — no annualization.

        Gross Revenue
        − VAT
        = Net Revenue (received + outstanding) + Planned
        − Business Expenses
        = Taxable Profit
        − Est. Income Tax
        = Safe to Spend

    If *projects* and *time_data* are given, planned revenue from future
    calendar events is included in the income basis.
    """
    today = datetime.date.today()
    is_past_year = year is not None and year < today.year

    if year is not None and is_past_year:
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
    if not is_past_year and projects and time_data is not None:
        planned = compute_planned_revenue(projects, time_data, currency=currency)

    gross_ytd = received_gross + outstanding_gross
    vat_ytd = received_vat + outstanding_vat
    net_ytd = received_net + outstanding_net

    if is_past_year:
        months_elapsed = 12
    else:
        months_elapsed = max(
            (today.year - year_start.year) * 12 + today.month - year_start.month + 1,
            1,
        )

    # Compute YTD business expenses from the fixed-amount recurring expenses
    fixed_expenses = [e for e in (expenses or []) if e.rate is None]
    dynamic_expenses = [e for e in (expenses or []) if e.rate is not None]
    biz_expenses_ytd = (_monthly_expenses_total(fixed_expenses) * months_elapsed).quantize(Decimal("0.01"))

    taxable_profit = net_ytd + planned - biz_expenses_ytd

    # Dynamic expenses are charged on income actually earned so far, so planned
    # calendar revenue stays out of their base even though it is taxed.
    dynamic_base_monthly = (net_ytd - biz_expenses_ytd) / months_elapsed

    deductible_lines = _dynamic_lines(dynamic_expenses, dynamic_base_monthly, deductible=True)
    dyn_deductible = (_lines_total(deductible_lines) * months_elapsed).quantize(Decimal("0.01"))

    # Deductible provisions (health insurance, Rürup) shrink the income the tax
    # is assessed on; the rest is paid out of money that was already taxed.
    tax_base = taxable_profit - dyn_deductible
    tax_reserve = compute_income_tax_reserve(tax_base, country, deductions, year=year)

    post_tax = tax_base - tax_reserve.ytd_reserve
    post_tax_lines = _dynamic_lines(dynamic_expenses, post_tax / months_elapsed, deductible=False)
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
        conversion_fee=conversion_fee,
        dynamic_expenses_deductible=dyn_deductible,
        dynamic_expenses_post_tax=dyn_post_tax,
        tax_base=tax_base,
        dynamic_expenses=dynamic_lines,
    )


PERIOD_TO_MONTHS = {
    Cycle.monthly: Decimal(1),
    Cycle.quarterly: Decimal(3),
    Cycle.yearly: Decimal(12),
    Cycle.weekly: Decimal("0.25"),  # ~4.33 weeks/month → approx
    Cycle.daily: Decimal("30"),
    Cycle.hourly: Decimal("160"),  # rough ~160 work-hours/month
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


def _normalize_to_monthly(expense: RecurringExpense) -> Decimal:
    """Convert a recurring expense amount to its monthly equivalent."""
    divisor = PERIOD_TO_MONTHS.get(expense.period, Decimal(1))
    return (expense.amount / divisor).quantize(Decimal("0.01"))


def _monthly_expenses_total(expenses: List[RecurringExpense]) -> Decimal:
    """Sum all recurring expenses, normalized to a monthly amount."""
    return sum((_normalize_to_monthly(e) for e in expenses), Decimal(0))


class EffectiveSalary(NamedTuple):
    """The freelancer's safe-to-spend monthly salary, expressed as a range.

    conservative_monthly — floor: based only on revenue already received (paid invoices)
    optimistic_monthly   — ceiling: includes outstanding (unpaid, non-cancelled) invoices
    monthly_expenses     — normalized total of the fixed recurring expenses
    income_tax_reserve_monthly — prorated income-tax reserve per month
    vat_reserve_monthly        — prorated VAT reserve per month
    dynamic_expenses     — income-dependent expenses (health, pension), one line each
    currency             — ISO 4217 currency code
    """

    conservative_monthly: Decimal
    optimistic_monthly: Decimal
    monthly_expenses: Decimal
    income_tax_reserve_monthly: Decimal
    vat_reserve_monthly: Decimal
    currency: str
    dynamic_expenses: list = []  # per-expense DynamicExpenseLine, never mutated


def compute_effective_salary(
    invoices: List[Invoice],
    expenses: List[RecurringExpense],
    country: str,
    currency: Optional[str] = None,
) -> EffectiveSalary:
    """Compute the freelancer's effective monthly salary range.

    The *conservative* figure uses only paid invoices (certain, received revenue).
    The *optimistic* figure adds outstanding (sent but unpaid) invoices.
    Both are reduced by the prorated VAT reserve, income-tax reserve, and the
    total monthly recurring expenses.
    """
    today = datetime.date.today()
    year_start = today.replace(month=1, day=1)

    if currency is None:
        try:
            tax_system = get_tax_system(country, date=today)
            currency = tax_system.currency
        except NotImplementedError:
            currency = "EUR"

    months_elapsed = max((today.year - year_start.year) * 12 + today.month - year_start.month + 1, 1)

    gross_paid = Decimal(0)
    vat_paid = Decimal(0)
    gross_outstanding = Decimal(0)
    vat_outstanding = Decimal(0)

    for inv in invoices:
        if inv.cancelled:
            continue
        if inv.date < year_start:
            continue
        converted = convert_invoice(inv, currency)
        if converted is None:
            continue
        gross, vat = converted
        if inv.paid:
            gross_paid += gross
            vat_paid += vat
        else:
            gross_outstanding += gross
            vat_outstanding += vat

    net_paid = gross_paid - vat_paid
    net_all = net_paid + (gross_outstanding - vat_outstanding)

    monthly_vat_conservative = (vat_paid / months_elapsed).quantize(Decimal("0.01"))
    monthly_vat_optimistic = ((vat_paid + vat_outstanding) / months_elapsed).quantize(Decimal("0.01"))

    dynamic_expenses = [e for e in expenses if e.rate is not None]
    monthly_exp = _monthly_expenses_total([e for e in expenses if e.rate is None])

    def scenario(net: Decimal) -> tuple[Decimal, Decimal, List[DynamicExpenseLine]]:
        """Monthly salary, income-tax reserve and dynamic expense lines for a revenue basis."""
        base_monthly = net / months_elapsed - monthly_exp
        deductible_lines = _dynamic_lines(dynamic_expenses, base_monthly, deductible=True)
        dyn_deductible = _lines_total(deductible_lines)
        tax = compute_income_tax_reserve(net - dyn_deductible * months_elapsed, country)
        monthly_tax = (tax.ytd_reserve / months_elapsed).quantize(Decimal("0.01"))
        post_tax = base_monthly - dyn_deductible - monthly_tax
        post_tax_lines = _dynamic_lines(dynamic_expenses, post_tax, deductible=False)
        salary = (post_tax - _lines_total(post_tax_lines)).quantize(Decimal("0.01"))
        return salary, monthly_tax, deductible_lines + post_tax_lines

    conservative, monthly_tax_conservative, lines_conservative = scenario(net_paid)
    optimistic, monthly_tax_optimistic, lines_optimistic = scenario(net_all)

    # Both scenarios list the same expenses; the breakdown averages them, as the
    # tax and VAT rows already do.
    dynamic_lines = [
        con._replace(amount=((con.amount + opt.amount) / 2).quantize(Decimal("0.01")))
        for con, opt in zip(lines_conservative, lines_optimistic)
    ]
    # Use the average monthly figures for display breakdown
    avg_monthly_vat = ((monthly_vat_conservative + monthly_vat_optimistic) / 2).quantize(Decimal("0.01"))
    avg_monthly_tax = ((monthly_tax_conservative + monthly_tax_optimistic) / 2).quantize(Decimal("0.01"))

    return EffectiveSalary(
        conservative_monthly=conservative,
        optimistic_monthly=optimistic,
        monthly_expenses=monthly_exp,
        income_tax_reserve_monthly=avg_monthly_tax,
        vat_reserve_monthly=avg_monthly_vat,
        currency=currency,
        dynamic_expenses=dynamic_lines,
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
