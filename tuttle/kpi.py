"""Key Performance Indicators for freelance business analysis."""

import datetime
from decimal import Decimal
from typing import List, Optional, NamedTuple

from pandas import DataFrame

from .fx import primary_currency
from .model import Contract, Invoice, Project
from .time import TimeUnit
from .timetracking import sum_hours_by_tag
from .tax import get_tax_system
from .tax_reserves import compute_spendable_income, convert_invoice

from .app.core.formatting import fmt_currency


class KPISummary(NamedTuple):
    """Snapshot of key business metrics."""

    total_revenue: Decimal
    total_revenue_ytd: Decimal
    outstanding_amount: Decimal
    overdue_amount: Decimal
    effective_hourly_rate: Optional[Decimal]
    utilization_rate: Optional[float]
    active_projects: int
    active_contracts: int
    unpaid_invoices: int
    overdue_invoices: int
    # Tax reserves
    vat_reserve: Decimal
    income_tax_reserve: Decimal
    spendable_income: Decimal
    tax_currency: str = "EUR"

    def to_rpc_dict(self) -> dict:
        d = self._asdict()
        tc = self.tax_currency or "EUR"
        d["total_revenue_ytd_formatted"] = fmt_currency(self.total_revenue_ytd, tc)
        d["outstanding_amount_formatted"] = fmt_currency(self.outstanding_amount, tc)
        d["overdue_amount_formatted"] = fmt_currency(self.overdue_amount, tc)
        d["vat_reserve_formatted"] = fmt_currency(self.vat_reserve, tc)
        d["income_tax_reserve_formatted"] = fmt_currency(self.income_tax_reserve, tc)
        d["spendable_income_formatted"] = fmt_currency(self.spendable_income, tc)
        d["effective_hourly_rate_formatted"] = (
            fmt_currency(self.effective_hourly_rate, tc)
            if self.effective_hourly_rate is not None
            else "—"
        )
        d["utilization_rate_formatted"] = (
            f"{self.utilization_rate * 100:.0f}%"
            if self.utilization_rate is not None
            else "—"
        )
        return d


def compute_kpis(
    invoices: List[Invoice],
    contracts: List[Contract],
    projects: List[Project],
    country: str = "Germany",
    time_data: Optional[DataFrame] = None,
) -> KPISummary:
    """Compute business KPIs from invoices, contracts, and calendar data.

    *time_data* (the calendar DataFrame) is the source of truth for hours
    worked.  It drives ``effective_hourly_rate`` and ``utilization_rate``.
    Revenue metrics come from invoices, converted into the primary currency.
    """
    today = datetime.date.today()
    year_start = today.replace(month=1, day=1)

    currency = primary_currency(country)

    # Revenue metrics (from invoices)
    total_revenue = Decimal(0)
    total_revenue_ytd = Decimal(0)
    outstanding_amount = Decimal(0)
    overdue_amount = Decimal(0)
    unpaid_invoices = 0
    overdue_invoices = 0
    paid_revenue = Decimal(0)

    for inv in invoices:
        if inv.cancelled:
            continue
        converted = convert_invoice(inv, currency)
        if converted is None:
            continue
        inv_total = converted[0]

        if inv.paid:
            total_revenue += inv_total
            if inv.date >= year_start:
                total_revenue_ytd += inv_total
            paid_revenue += inv_total
        else:
            outstanding_amount += inv_total
            unpaid_invoices += 1
            if inv.due_date and inv.due_date < today:
                overdue_amount += inv_total
                overdue_invoices += 1

    # Total tracked hours from calendar data
    total_hours = Decimal(0)
    if time_data is not None and not time_data.empty:
        past = time_data[time_data.index.date < today]
        if not past.empty:
            tag_to_workday = {
                p.tag: p.contract.units_per_workday
                for p in projects
                if p.tag and p.contract
            }
            tracked = sum(sum_hours_by_tag(past, tag_to_workday).values())
            total_hours = Decimal(str(tracked))

    # Effective hourly rate: paid revenue / total tracked hours
    effective_hourly_rate = None
    if total_hours > 0:
        effective_hourly_rate = paid_revenue / total_hours

    # Active contracts / projects
    active_contracts = sum(1 for c in contracts if c.is_active())
    active_projects = sum(1 for p in projects if p.is_active())

    # Utilization rate: tracked hours / available hours (based on workdays)
    utilization_rate = None
    if active_contracts:
        days_elapsed = (today - year_start).days or 1
        workdays_elapsed = int(days_elapsed * 5 / 7)
        available_hours_per_day = sum(
            c.units_per_workday for c in contracts if c.is_active()
        )
        available_hours = Decimal(str(workdays_elapsed * available_hours_per_day))
        if available_hours > 0:
            utilization_rate = float(total_hours / available_hours)

    try:
        spending = compute_spendable_income(invoices, country, currency=currency)
        vat_reserve = spending.vat_reserve
        income_tax_reserve = spending.income_tax_reserve
        spendable_income = spending.spendable
    except NotImplementedError:
        vat_reserve = Decimal(0)
        income_tax_reserve = Decimal(0)
        spendable_income = Decimal(0)

    return KPISummary(
        total_revenue=total_revenue,
        total_revenue_ytd=total_revenue_ytd,
        outstanding_amount=outstanding_amount,
        overdue_amount=overdue_amount,
        effective_hourly_rate=effective_hourly_rate,
        utilization_rate=utilization_rate,
        active_projects=active_projects,
        active_contracts=active_contracts,
        unpaid_invoices=unpaid_invoices,
        overdue_invoices=overdue_invoices,
        vat_reserve=vat_reserve,
        income_tax_reserve=income_tax_reserve,
        spendable_income=spendable_income,
        tax_currency=currency,
    )


def monthly_revenue_breakdown(
    invoices: List[Invoice],
    n_months: int = 12,
    country: str = "Germany",
) -> list:
    """Revenue breakdown by month for the last n_months, in the primary currency.

    Returns a list of dicts with keys: month, revenue, pipeline, invoice_count.
    ``revenue`` is paid invoices; ``pipeline`` is sent-but-unpaid invoices.
    """
    today = datetime.date.today()
    currency = primary_currency(country)
    start = (today - datetime.timedelta(days=30 * n_months)).replace(day=1)

    months = {}
    current = start
    while current <= today:
        key = current.strftime("%Y-%m")
        months[key] = {
            "month": key,
            "revenue": Decimal(0),
            "pipeline": Decimal(0),
            "invoice_count": 0,
        }
        current = (current + datetime.timedelta(days=32)).replace(day=1)

    for inv in invoices:
        if inv.cancelled:
            continue
        key = inv.date.strftime("%Y-%m")
        if key not in months:
            continue
        converted = convert_invoice(inv, currency)
        if converted is None:
            continue
        if inv.paid:
            months[key]["revenue"] += converted[0]
            months[key]["invoice_count"] += 1
        elif inv.sent:
            months[key]["pipeline"] += converted[0]

    return sorted(months.values(), key=lambda x: x["month"])


def monthly_spendable_breakdown(
    invoices: List[Invoice],
    country: str = "Germany",
    n_months: int = 12,
    deductions: Decimal = Decimal(0),
) -> list:
    """Estimate monthly spendable income after VAT and income-tax true-up.

    For each month bucket this returns:
    - gross_revenue: invoiced amount including VAT
    - vat_due: VAT to reserve for that month
    - net_revenue: gross_revenue - vat_due
    - income_tax_true_up: monthly delta in YTD tax reserve estimate
    - spendable: net_revenue - income_tax_true_up
    """
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=30 * n_months)).replace(day=1)

    months = {}
    current = start
    while current <= today:
        key = current.strftime("%Y-%m")
        months[key] = {
            "month": key,
            "gross_revenue": Decimal(0),
            "vat_due": Decimal(0),
            "net_revenue": Decimal(0),
            "income_tax_true_up": Decimal(0),
            "spendable": Decimal(0),
            "invoice_count": 0,
        }
        current = (current + datetime.timedelta(days=32)).replace(day=1)

    # Foreign-currency invoices are converted into the primary currency at the
    # ECB monthly average, not dropped.
    currency = primary_currency(country)

    for inv in invoices:
        if inv.cancelled or not inv.paid:
            continue
        key = inv.date.strftime("%Y-%m")
        if key in months:
            converted = convert_invoice(inv, currency)
            if converted is None:
                continue
            months[key]["gross_revenue"] += converted[0]
            months[key]["vat_due"] += converted[1]
            months[key]["invoice_count"] += 1

    sorted_keys = sorted(months.keys())
    cumulative_net_ytd = Decimal(0)
    previous_reserve = Decimal(0)

    for key in sorted_keys:
        m = months[key]
        m["net_revenue"] = m["gross_revenue"] - m["vat_due"]
        year_str, month_str = key.split("-")
        month_start = datetime.date(int(year_str), int(month_str), 1)
        if month_start.year == today.year:
            cumulative_net_ytd += m["net_revenue"]
            taxable = cumulative_net_ytd - deductions
            if taxable <= 0:
                cumulative_reserve = Decimal(0)
            else:
                try:
                    month_end = (month_start + datetime.timedelta(days=32)).replace(
                        day=1
                    ) - datetime.timedelta(days=1)
                    as_of = min(month_end, today)
                    tax_system = get_tax_system(country, date=as_of)
                    annual_tax = tax_system.income_tax(taxable)
                    annual_soli = tax_system.solidarity_surcharge(annual_tax)
                    cumulative_reserve = (annual_tax + annual_soli).quantize(
                        Decimal("0.01")
                    )
                except NotImplementedError:
                    cumulative_reserve = Decimal(0)

            m["income_tax_true_up"] = cumulative_reserve - previous_reserve
            previous_reserve = cumulative_reserve
        else:
            m["income_tax_true_up"] = Decimal(0)

        m["spendable"] = m["net_revenue"] - m["income_tax_true_up"]

    return [months[k] for k in sorted_keys]


def project_budget_status(
    projects: List[Project],
    time_data: Optional[DataFrame] = None,
) -> list:
    """Budget utilization per project derived from calendar time-tracking data.

    *time_data* (the calendar DataFrame) is the source of truth for hours.
    Past events (before now) become ``hours_tracked``; future events
    become ``hours_planned``.

    Returns a list of dicts with keys: project_id, project, hours_tracked,
    hours_planned, hours_budget, hours_remaining, planned_revenue, progress,
    budget_exceeded.  Skips projects without a contract volume or without any
    tracked or planned time.
    """
    now = datetime.datetime.now()
    tracked_by_tag: dict = {}
    planned_by_tag: dict = {}

    if time_data is not None and not time_data.empty:
        tag_to_workday = {
            p.tag: p.contract.units_per_workday
            for p in projects
            if p.tag and p.contract
        }
        past = time_data[time_data.index < now]
        if not past.empty:
            tracked_by_tag = sum_hours_by_tag(past, tag_to_workday)
        future = time_data[time_data.index >= now]
        if not future.empty:
            planned_by_tag = sum_hours_by_tag(future, tag_to_workday)

    results = []
    for project in projects:
        if not project.contract:
            continue

        hours_tracked = Decimal(str(tracked_by_tag.get(project.tag, 0)))
        hours_planned = Decimal(str(planned_by_tag.get(project.tag, 0)))

        if hours_tracked == 0 and hours_planned == 0:
            continue

        contract = project.contract
        open_ended = not contract.volume

        if open_ended:
            hours_budget = Decimal(0)
        else:
            hours_budget = Decimal(str(contract.volume))
            if contract.unit == TimeUnit.day:
                hours_budget *= contract.units_per_workday

        total_used = hours_tracked + hours_planned
        progress = (
            1.0
            if open_ended
            else (float(total_used / hours_budget) if hours_budget > 0 else 0.0)
        )
        hours_remaining = 0.0 if open_ended else float(hours_budget - total_used)

        unit_hours = contract.units_per_workday if contract.unit == TimeUnit.day else 1
        planned_revenue = (
            float(Decimal(str(float(hours_planned) / unit_hours)) * contract.rate)
            if contract.rate
            else 0.0
        )

        budget_exceeded = not open_ended and total_used > hours_budget

        results.append(
            {
                "project_id": project.id,
                "project": project.title,
                "hours_tracked": float(hours_tracked),
                "hours_planned": float(hours_planned),
                "hours_budget": float(hours_budget),
                "hours_remaining": hours_remaining,
                "planned_revenue": round(planned_revenue, 2),
                "currency": str(contract.currency) if contract.currency else "EUR",
                "progress": min(progress, 1.0),
                "budget_exceeded": budget_exceeded,
                "open_ended": open_ended,
            }
        )
    return results
