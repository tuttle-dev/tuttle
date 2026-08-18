"""Revenue forecasting based on contracts, time allocation, and invoices."""

import calendar
import datetime
from decimal import Decimal
from typing import List, Optional

import pandas
from pandas import DataFrame

from .fx import primary_currency
from .model import Contract, Invoice, Project
from .tax_reserves import convert_invoice
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


def revenue_from_calendar(
    time_data: Optional[DataFrame],
    projects: List[Project],
    start_date: datetime.date,
    end_date: datetime.date,
    invoices: Optional[List[Invoice]] = None,
    freq: str = "M",
) -> DataFrame:
    """Derive revenue per time bucket from calendar time-tracking events.

    The calendar DataFrame is the source of truth for hours worked (past)
    and hours planned (future).  Filters *time_data* for events in
    [start_date, end_date], groups by *freq* period and project tag, then
    converts hours to revenue via contract rates.  *freq* is a pandas
    period alias — "W", "M" or "Y".

    If *invoices* is given, hours already captured in a timesheet attached
    to a (non-cancelled) invoice are excluded, keyed by the timesheet's own
    period rather than the invoice's date — otherwise work billed in a
    later month than it was performed would show up twice: once as
    "planned" for the month it was done, and again as "invoiced" for the
    month the invoice was actually raised.

    Returns a DataFrame with columns: period, project, revenue, contract_id, hours.
    """
    empty = DataFrame(columns=["period", "project", "revenue", "contract_id", "hours"])
    if time_data is None or time_data.empty:
        return empty

    tag_to_project = {p.tag: p for p in projects if p.tag and p.contract}

    index_dates = time_data.index.date
    mask = (index_dates >= start_date) & (index_dates <= end_date)
    filtered = time_data[mask]
    if filtered.empty:
        return empty

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
                return empty

    records = []
    df = filtered.copy()
    df["_period"] = pandas.to_datetime(df.index).to_period(freq).to_timestamp()
    df["_hours"] = df.apply(
        lambda row: event_hours(
            row,
            tag_to_project[row["tag"]].contract.units_per_workday if row["tag"] in tag_to_project else 8,
        ),
        axis=1,
    )

    grouped = df.groupby(["_period", "tag"]).agg(hours=("_hours", "sum")).reset_index()
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
                "period": row["_period"],
                "project": project.title,
                "revenue": revenue,
                "contract_id": contract.id,
                "hours": round(row["hours"], 1),
            }
        )

    if not records:
        return empty
    return DataFrame(records)


def monthly_revenue_from_calendar(
    time_data: Optional[DataFrame],
    projects: List[Project],
    start_date: datetime.date,
    end_date: datetime.date,
    invoices: Optional[List[Invoice]] = None,
) -> DataFrame:
    """Monthly view of :func:`revenue_from_calendar`, keyed by ``month``.

    Returns a DataFrame with columns: month, project, revenue, contract_id, hours.
    """
    df = revenue_from_calendar(time_data, projects, start_date, end_date, invoices=invoices, freq="M")
    return df.rename(columns={"period": "month"})


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


# Bucket sizes per granularity: pandas period alias, buckets per window, and
# how many of those buckets sit in the future when viewing the present.
_GRANULARITY = {
    "week": ("W", 13, 3),
    "month": ("M", 16, 3),
    "year": ("Y", 0, 0),
}


def revenue_window(
    granularity: str,
    offset: int = 0,
    today: Optional[datetime.date] = None,
) -> tuple:
    """Start and end date of the visible window for a paged revenue chart.

    *offset* pages the window: 0 is the window containing today, -1 the one
    before it, and so on.  A month window spans 16 buckets and a week window
    13, both reaching three buckets into the future at offset 0 so planned
    work is visible.  Any 16 consecutive months contain a January, so the
    month view always has a year boundary on screen.
    """
    today = today or datetime.date.today()
    freq, size, ahead = _GRANULARITY[granularity]
    if size == 0:
        raise ValueError(f"{granularity} is not a paged granularity")

    current = pandas.Period(today, freq=freq)
    last = current + ahead + offset * size
    first = last - (size - 1)
    return first.start_time.date(), last.end_time.date()


def _data_extent(
    invoices: List[Invoice],
    time_data: Optional[DataFrame],
) -> tuple:
    """Earliest and latest date covered by invoices or calendar events."""
    dates = [inv.date for inv in invoices if not inv.cancelled and inv.date]
    if time_data is not None and not time_data.empty:
        dates.append(time_data.index.min().date())
        dates.append(time_data.index.max().date())
    if not dates:
        return None, None
    return min(dates), max(dates)


def _bucket_label(start: datetime.date, granularity: str) -> str:
    if granularity == "week":
        return f"W{start.isocalendar()[1]:02d}"
    if granularity == "year":
        return str(start.year)
    return calendar.month_abbr[start.month]


def revenue_series(
    invoices: List[Invoice],
    projects: List[Project],
    time_data: Optional[DataFrame],
    granularity: str = "month",
    offset: int = 0,
    country: str = "",
    today: Optional[datetime.date] = None,
) -> dict:
    """Received, invoiced and planned revenue per bucket for one chart window.

    Reconciles the two revenue sources the dashboard chart needs into a
    single series so the frontend does not have to join them: invoices give
    ``received`` (paid) and ``invoiced`` (sent but unpaid) keyed by invoice
    date, while the calendar gives ``planned`` — tracked or scheduled work
    that no timesheet has billed yet, in the past as well as the future.

    *granularity* is "week", "month" or "year".  Week and month windows are
    paged with *offset*; the year window always spans the full data extent.
    Empty buckets are included so the time axis stays continuous.
    """
    if granularity not in _GRANULARITY:
        raise ValueError(f"unknown granularity: {granularity}")

    today = today or datetime.date.today()
    freq = _GRANULARITY[granularity][0]
    currency = primary_currency(country)
    extent_start, extent_end = _data_extent(invoices, time_data)

    if granularity == "year":
        first_year = min(extent_start.year if extent_start else today.year, today.year)
        last_year = max(extent_end.year if extent_end else today.year, today.year)
        window_start = datetime.date(first_year, 1, 1)
        window_end = datetime.date(last_year, 12, 31)
    else:
        window_start, window_end = revenue_window(granularity, offset, today=today)

    periods = pandas.period_range(start=window_start, end=window_end, freq=freq)
    buckets = {
        p: {
            "bucket": p.start_time.date().isoformat(),
            "bucket_end": p.end_time.date().isoformat(),
            "label": _bucket_label(p.start_time.date(), granularity),
            "year": p.start_time.year,
            "received": 0.0,
            "invoiced": 0.0,
            "planned": 0.0,
            "invoice_count": 0,
            "hours": 0.0,
        }
        for p in periods
    }

    for inv in invoices:
        if inv.cancelled or not inv.date:
            continue
        period = pandas.Period(inv.date, freq=freq)
        bucket = buckets.get(period)
        if bucket is None:
            continue
        converted = convert_invoice(inv, currency)
        if converted is None:
            continue
        if inv.paid:
            bucket["received"] += float(converted[0])
            bucket["invoice_count"] += 1
        elif inv.sent:
            bucket["invoiced"] += float(converted[0])
            bucket["invoice_count"] += 1

    cal = revenue_from_calendar(time_data, projects, window_start, window_end, invoices=invoices, freq=freq)
    if not cal.empty:
        grouped = cal.groupby("period").agg(revenue=("revenue", "sum"), hours=("hours", "sum")).reset_index()
        for _, row in grouped.iterrows():
            bucket = buckets.get(pandas.Period(row["period"], freq=freq))
            if bucket is None:
                continue
            bucket["planned"] += max(0.0, float(row["revenue"]))
            bucket["hours"] += float(row["hours"])

    current_period = pandas.Period(today, freq=freq)
    rows = []
    previous_year = None
    for period in periods:
        row = buckets[period]
        row["is_current"] = period == current_period
        row["is_future"] = period > current_period
        row["is_year_start"] = previous_year is not None and row["year"] != previous_year
        row["total"] = round(row["received"] + row["invoiced"] + row["planned"], 2)
        for key in ("received", "invoiced", "planned", "hours"):
            row[key] = round(row[key], 2)
        previous_year = row["year"]
        rows.append(row)

    paged = granularity != "year"
    return {
        "granularity": granularity,
        "offset": offset,
        "currency": currency,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "buckets": rows,
        "total": round(sum(r["total"] for r in rows), 2),
        "has_earlier": bool(paged and extent_start and extent_start < window_start),
        "has_later": bool(paged and offset < 0),
    }
