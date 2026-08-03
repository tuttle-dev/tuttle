"""Revenue forecasting based on contracts, time allocation, and invoices."""

import datetime
from decimal import Decimal
from typing import List, Optional

import pandas
from pandas import DataFrame

from .model import Contract, Invoice, Project
from .time import TimeUnit
from .timetracking import event_hours


def monthly_revenue_from_contracts(
    contracts: List[Contract],
    start_date: datetime.date,
    end_date: datetime.date,
) -> DataFrame:
    """Project monthly revenue from active contracts and their rates.

    For each month in [start_date, end_date], estimates revenue based on
    contract rate × volume distributed across the contract duration.

    Returns a DataFrame with columns: month, project, revenue, contract_id.
    """
    records = []
    current = start_date.replace(day=1)
    while current <= end_date:
        month_end = (current + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
        for contract in contracts:
            if contract.start_date > month_end:
                continue
            if contract.end_date and contract.end_date < current:
                continue
            if contract.is_completed:
                continue

            workdays_in_month = 22

            if contract.volume and contract.start_date and contract.end_date:
                total_days = (contract.end_date - contract.start_date).days or 1
                contract_months = max(total_days / 30.0, 1.0)
                billable_units = contract.volume / contract_months
            elif contract.unit == TimeUnit.day:
                billable_units = workdays_in_month
            else:
                billable_units = workdays_in_month * contract.units_per_workday

            monthly_revenue = Decimal(str(billable_units)) * contract.rate
            project_title = contract.projects[0].title if contract.projects else contract.title

            records.append(
                {
                    "month": current,
                    "project": project_title,
                    "revenue": float(monthly_revenue),
                    "contract_id": contract.id,
                }
            )
        current = (current + datetime.timedelta(days=32)).replace(day=1)

    if not records:
        return DataFrame(columns=["month", "project", "revenue", "contract_id"])
    return DataFrame(records)


def revenue_history(
    invoices: List[Invoice],
) -> DataFrame:
    """Build a monthly revenue history from past invoices.

    Returns a DataFrame with columns: month, revenue, invoice_count.
    """
    if not invoices:
        return DataFrame(columns=["month", "revenue", "invoice_count"])

    records = []
    for inv in invoices:
        if inv.cancelled:
            continue
        records.append(
            {
                "date": inv.date,
                "revenue": float(inv.total),
            }
        )

    if not records:
        return DataFrame(columns=["month", "revenue", "invoice_count"])

    df = DataFrame(records)
    df["month"] = pandas.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    monthly = (
        df.groupby("month")
        .agg(
            revenue=("revenue", "sum"),
            invoice_count=("revenue", "count"),
        )
        .reset_index()
    )
    return monthly


def revenue_curve(
    invoices: List[Invoice],
    contracts: List[Contract],
    forecast_months: int = 6,
) -> DataFrame:
    """Combine historical revenue with forecast into a single time series.

    Returns a DataFrame with columns: month, revenue, is_forecast.
    """
    # Historical
    history = revenue_history(invoices)
    if not history.empty:
        history["is_forecast"] = False
    else:
        history = DataFrame(columns=["month", "revenue", "is_forecast"])

    # Forecast
    today = datetime.date.today()
    forecast_start = today.replace(day=1)
    forecast_end = (forecast_start + datetime.timedelta(days=30 * forecast_months)).replace(day=1)
    forecast = monthly_revenue_from_contracts(contracts, forecast_start, forecast_end)
    if not forecast.empty:
        forecast_monthly = forecast.groupby("month").agg(revenue=("revenue", "sum")).reset_index()
        forecast_monthly["is_forecast"] = True
    else:
        forecast_monthly = DataFrame(columns=["month", "revenue", "is_forecast"])

    combined = pandas.concat([history, forecast_monthly], ignore_index=True)
    combined["month"] = pandas.to_datetime(combined["month"])
    combined = combined.sort_values("month").reset_index(drop=True)

    # Cumulative revenue
    combined["cumulative_revenue"] = combined["revenue"].cumsum()

    return combined


def _invoiced_ranges_by_tag(invoices: List[Invoice]) -> dict:
    """Map project tag -> list of (period_start, period_end) already invoiced.

    A timesheet's period is the exact slice of calendar hours that were
    pulled into an invoice, regardless of the invoice's own date (an
    invoice raised in August can cover a timesheet for July). Cancelled
    invoices don't count: their hours are still un-invoiced.
    """
    ranges: dict = {}
    for inv in invoices:
        if inv.cancelled:
            continue
        for ts in inv.timesheets:
            tag = ts.project.tag if ts.project else None
            if not tag:
                continue
            ranges.setdefault(tag, []).append((ts.period_start, ts.period_end))
    return ranges


def monthly_revenue_from_calendar(
    time_data: DataFrame,
    projects: List[Project],
    start_date: datetime.date,
    end_date: datetime.date,
    invoices: Optional[List[Invoice]] = None,
) -> DataFrame:
    """Derive monthly revenue from calendar time-tracking events.

    The calendar DataFrame is the source of truth for hours worked (past)
    and hours planned (future).  Filters *time_data* for events in
    [start_date, end_date], groups by month and project tag, then converts
    hours to revenue via contract rates.

    If *invoices* is given, hours already captured in a timesheet attached
    to a (non-cancelled) invoice are excluded, keyed by the timesheet's own
    period rather than the invoice's date — otherwise work billed in a
    later month than it was performed would show up twice: once as
    "planned" for the month it was done, and again as "invoiced" for the
    month the invoice was actually raised.

    Returns a DataFrame with columns: month, project, revenue, contract_id, hours.
    """
    if time_data is None or time_data.empty:
        return DataFrame(columns=["month", "project", "revenue", "contract_id", "hours"])

    tag_to_project = {p.tag: p for p in projects if p.tag and p.contract}

    index_dates = time_data.index.date
    mask = (index_dates >= start_date) & (index_dates <= end_date)
    filtered = time_data[mask]
    if filtered.empty:
        return DataFrame(columns=["month", "project", "revenue", "contract_id", "hours"])

    if invoices:
        invoiced_ranges = _invoiced_ranges_by_tag(invoices)
        if invoiced_ranges:
            dates = filtered.index.date
            tags = filtered["tag"]
            already_invoiced = [
                any(start <= d <= end for start, end in invoiced_ranges.get(tag, ())) for d, tag in zip(dates, tags)
            ]
            filtered = filtered[[not v for v in already_invoiced]]
            if filtered.empty:
                return DataFrame(columns=["month", "project", "revenue", "contract_id", "hours"])

    records = []
    df = filtered.copy()
    df["_month"] = pandas.to_datetime(df.index).to_period("M").to_timestamp()
    df["_hours"] = df.apply(
        lambda row: event_hours(
            row,
            tag_to_project[row["tag"]].contract.units_per_workday if row["tag"] in tag_to_project else 8,
        ),
        axis=1,
    )

    grouped = df.groupby(["_month", "tag"]).agg(hours=("_hours", "sum")).reset_index()
    for _, row in grouped.iterrows():
        tag = row["tag"]
        project = tag_to_project.get(tag)
        if not project:
            continue
        contract = project.contract
        unit_hours = contract.units_per_workday if contract.unit == TimeUnit.day else 1
        billable_units = row["hours"] / unit_hours
        revenue = float(Decimal(str(billable_units)) * contract.rate)
        records.append(
            {
                "month": row["_month"],
                "project": project.title,
                "revenue": revenue,
                "contract_id": contract.id,
                "hours": round(row["hours"], 1),
            }
        )

    if not records:
        return DataFrame(columns=["month", "project", "revenue", "contract_id", "hours"])
    return DataFrame(records)


def cash_flow_projection(
    revenue_forecast: DataFrame,
    contracts: List[Contract],
) -> DataFrame:
    """Shift a monthly revenue forecast forward by each contract's payment terms.

    Takes the output of ``monthly_revenue_from_calendar`` or
    ``monthly_revenue_from_contracts`` and produces expected cash inflows.

    Returns a DataFrame with columns: month, expected_inflow, contract_id.
    """
    if revenue_forecast.empty:
        return DataFrame(columns=["month", "expected_inflow", "contract_id"])

    contract_map = {c.id: c for c in contracts if c.id is not None}
    records = []
    for _, row in revenue_forecast.iterrows():
        cid = row.get("contract_id")
        contract = contract_map.get(cid)
        payment_delay = contract.term_of_payment if contract else 31
        revenue_month = pandas.Timestamp(row["month"])
        inflow_date = revenue_month + pandas.DateOffset(days=payment_delay)
        inflow_month = inflow_date.to_period("M").to_timestamp()
        records.append(
            {
                "month": inflow_month,
                "expected_inflow": row["revenue"],
                "contract_id": cid,
            }
        )

    if not records:
        return DataFrame(columns=["month", "expected_inflow", "contract_id"])

    df = DataFrame(records)
    return (
        df.groupby("month")
        .agg(
            expected_inflow=("expected_inflow", "sum"),
        )
        .reset_index()
        .sort_values("month")
        .reset_index(drop=True)
    )


def revenue_curve_with_calendar(
    invoices: List[Invoice],
    contracts: List[Contract],
    projects: List[Project],
    time_data: Optional[DataFrame],
    forecast_months: int = 6,
) -> DataFrame:
    """Revenue curve combining invoice history with calendar-derived revenue.

    The calendar DataFrame is the source of truth for hours worked and
    planned.  Calendar-derived revenue covers the full date range of
    *time_data* (both past and future), so months without invoices still
    show revenue from tracked work.  Invoice-based rows are labelled
    ``source="actual"``; calendar-based rows ``source="calendar"``.
    """
    history = revenue_history(invoices)
    if not history.empty:
        history["is_forecast"] = False
        history["source"] = "actual"
    else:
        history = DataFrame(columns=["month", "revenue", "is_forecast", "source"])

    today = datetime.date.today()
    forecast_end = (today.replace(day=1) + datetime.timedelta(days=30 * forecast_months)).replace(day=1)

    cal_monthly = DataFrame(columns=["month", "revenue", "is_forecast", "source"])
    if time_data is not None and not time_data.empty:
        cal_start = time_data.index.min().date().replace(day=1)
        cal_revenue = monthly_revenue_from_calendar(time_data, projects, cal_start, forecast_end, invoices=invoices)
        if not cal_revenue.empty:
            cal_monthly = cal_revenue.groupby("month").agg(revenue=("revenue", "sum")).reset_index()
            cal_monthly["is_forecast"] = cal_monthly["month"] >= pandas.Timestamp(today.replace(day=1))
            cal_monthly["source"] = "calendar"

    combined = pandas.concat([history, cal_monthly], ignore_index=True)
    combined["month"] = pandas.to_datetime(combined["month"])
    combined = combined.sort_values("month").reset_index(drop=True)
    combined["cumulative_revenue"] = combined["revenue"].cumsum()
    return combined
