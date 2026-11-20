"""Key Performance Indicators for freelance business analysis."""

import datetime
from decimal import Decimal
from typing import List, NamedTuple, Optional

from pandas import DataFrame, Timestamp

from .forecasting import contracted_this_year
from .fx import primary_currency
from .model import Contract, Invoice, Project, RecurringExpense
from .tax_reserves import compute_planned_revenue, compute_spendable_income, convert_invoice, distinct
from .time import TimeUnit
from .timetracking import sum_hours_by_tag


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
    income_tax_reserve: Optional[Decimal]  # None without tax rules
    spendable_income: Optional[Decimal]  # None without tax rules
    # The year's income, net of VAT, by how certain it is; together the income basis of Spendable Income
    received_net: Decimal = Decimal(0)
    invoiced_net: Decimal = Decimal(0)  # issued, not yet paid
    planned_revenue: Decimal = Decimal(0)  # tracked or scheduled work, not yet invoiced
    contracted_revenue: Decimal = Decimal(0)
    # Everything taken off that income besides the income tax; None without tax rules
    expenses: Optional[Decimal] = None
    ready_to_invoice: Decimal = Decimal(0)  # the tracked part of planned_revenue
    tax_currency: str = "EUR"
    country_supported: bool = True  # whether there are tax rules to estimate income tax with
    country: str = ""
    tax_unavailable_reason: Optional[str] = None
    unconverted: list = []  # amounts left out for lack of an exchange rate, one line each; never mutated

    def to_rpc_dict(self) -> dict:
        # The dashboard formats the amounts itself.
        return self._asdict()


def compute_kpis(
    invoices: List[Invoice],
    contracts: List[Contract],
    projects: List[Project],
    country: str = "",
    time_data: Optional[DataFrame] = None,
    expenses: Optional[List[RecurringExpense]] = None,
) -> KPISummary:
    """Compute business KPIs from invoices, contracts, and calendar data.

    *time_data* (the calendar DataFrame) is the source of truth for hours
    worked.  It drives ``effective_hourly_rate`` and ``utilization_rate``.
    Revenue metrics come from invoices, converted into the primary currency:
    revenue is net of VAT, while the outstanding and overdue amounts are what
    clients still owe, VAT included. Amounts without an exchange rate are left
    out of every figure, and ``unconverted`` names them.
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
    left_out: list = []

    for inv in invoices:
        if not inv.is_counted:
            continue
        converted = convert_invoice(inv, currency, left_out)
        if converted is None:
            continue
        inv_total, inv_vat = converted

        if inv.paid:
            revenue = inv_total - inv_vat
            total_revenue += revenue
            if inv.revenue_date >= year_start:
                total_revenue_ytd += revenue
            paid_revenue += revenue
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
            tag_to_workday = {p.tag: p.contract.units_per_workday for p in projects if p.tag and p.contract}
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
        available_hours_per_day = sum(c.units_per_workday for c in contracts if c.is_active())
        available_hours = Decimal(str(workdays_elapsed * available_hours_per_day))
        if available_hours > 0:
            utilization_rate = float(total_hours / available_hours)

    # The same inputs as the Tax page, so Spendable Income equals its Safe to Spend.
    spending = compute_spendable_income(
        invoices,
        country,
        expenses=expenses,
        currency=currency,
        projects=projects,
        time_data=time_data,
        contracted=contracted_this_year(projects, invoices, time_data, currency=currency, left_out=left_out),
        left_out=left_out,
    )
    # Received, invoiced, planned and contracted, less the income tax and these, leave Spendable Income.
    expenses = None
    if spending.dynamic_expenses_post_tax is not None:
        expenses = (
            spending.business_expenses
            + spending.dynamic_expenses_deductible
            + spending.fixed_expenses_post_tax
            + spending.dynamic_expenses_post_tax
            + spending.conversion_fee
        )
    ready_to_invoice = compute_planned_revenue(projects, time_data, currency=currency, invoices=invoices, tracked_only=True)
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
        vat_reserve=spending.vat_reserve,
        income_tax_reserve=spending.income_tax_reserve,
        spendable_income=spending.spendable,
        received_net=spending.received_net,
        invoiced_net=spending.outstanding_net,
        planned_revenue=spending.planned_revenue,
        contracted_revenue=spending.contracted_revenue,
        expenses=expenses,
        ready_to_invoice=ready_to_invoice,
        tax_currency=currency,
        country_supported=spending.tax_unavailable_reason is None,
        country=country,
        tax_unavailable_reason=spending.tax_unavailable_reason,
        unconverted=distinct(left_out),
    )


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
    tracked_by_tag: dict = {}
    planned_by_tag: dict = {}

    if time_data is not None and not time_data.empty:
        # Calendar indexes are timezone-aware; a naive "now" cannot be compared with them.
        now = Timestamp.now(tz=time_data.index.tz)
        tag_to_workday = {p.tag: p.contract.units_per_workday for p in projects if p.tag and p.contract}
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
        progress = 1.0 if open_ended else (float(total_used / hours_budget) if hours_budget > 0 else 0.0)
        hours_remaining = 0.0 if open_ended else float(hours_budget - total_used)

        unit_hours = contract.units_per_workday if contract.unit == TimeUnit.day else 1
        planned_revenue = float(Decimal(str(float(hours_planned) / unit_hours)) * contract.rate) if contract.rate else 0.0

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
