"""Revenue forecasting based on contracts, time allocation, and invoices."""

import calendar
import datetime
from decimal import Decimal
from typing import List, NamedTuple, Optional

import pandas
from pandas import DataFrame

from .fx import convert, primary_currency, rate
from .model import Contract, Invoice, Project, RecurringExpense
from .tax_reserves import (
    _dynamic_lines,
    _lines_total,
    _monthly_expenses_total,
    compute_income_tax_reserve,
    convert_invoice,
)
from .time import TimeUnit
from .timetracking import drop_completed, drop_invoiced, event_hours


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

            if not contract.rate:
                continue
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


def revenue_from_calendar(
    time_data: Optional[DataFrame],
    projects: List[Project],
    start_date: datetime.date,
    end_date: datetime.date,
    invoices: Optional[List[Invoice]] = None,
    freq: str = "M",
    currency: Optional[str] = None,
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

    Completed projects are left out: they are invoiced and paid in full.

    If *currency* is given, revenue from a contract in another currency is
    converted at the current month's rate (uninvoiced work has no invoice
    date to pin a rate to), the same as the tax view's planned revenue.
    Work whose rate cannot be resolved is left out rather than mixed in.

    Returns a DataFrame with columns: period, project, revenue, contract_id, hours.
    """
    empty = DataFrame(columns=["period", "project", "revenue", "contract_id", "hours"])
    if time_data is None or time_data.empty:
        return empty

    tag_to_project = {p.tag: p for p in projects if p.tag and p.contract}

    index_dates = time_data.index.date
    mask = (index_dates >= start_date) & (index_dates <= end_date)
    filtered = drop_completed(time_data[mask], projects)
    if filtered.empty:
        return empty

    if invoices:
        filtered = drop_invoiced(filtered, invoices)
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
        if not contract.rate:
            continue
        unit_hours = contract.units_per_workday if contract.unit == TimeUnit.day else 1
        billable_units = row["hours"] / unit_hours
        revenue = Decimal(str(billable_units)) * contract.rate
        if currency and contract.currency not in (currency, None):
            revenue = convert(revenue, contract.currency, currency, datetime.date.today())
            if revenue is None:
                continue
        records.append(
            {
                "period": row["_period"],
                "project": project.title,
                "revenue": float(revenue),
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
    currency: Optional[str] = None,
) -> DataFrame:
    """Monthly view of :func:`revenue_from_calendar`, keyed by ``month``.

    Returns a DataFrame with columns: month, project, revenue, contract_id, hours.
    """
    df = revenue_from_calendar(time_data, projects, start_date, end_date, invoices=invoices, freq="M", currency=currency)
    return df.rename(columns={"period": "month"})


class ContractedSlice(NamedTuple):
    """Contracted revenue of one contract, spread evenly over the days from *start* to *end*."""

    contract: Contract
    start: datetime.date
    end: datetime.date
    amount: float  # net, in the primary currency


def _committed_contracts(projects: List[Project], today: datetime.date) -> list:
    """(contract, its projects) for each open contract with a project past Lead and Offer."""
    groups: dict = {}
    for project in projects:
        contract = project.contract
        if contract is None:
            continue
        key = contract.id if contract.id is not None else id(contract)
        groups.setdefault(key, (contract, []))[1].append(project)
    return [
        (contract, members)
        for contract, members in groups.values()
        if not contract.is_completed and any(p.is_committed(today) for p in members)
    ]


def _term_end(contract: Contract, members: List[Project]) -> Optional[datetime.date]:
    """Last day of the contract's term: its end date, else the latest end date of its projects."""
    if contract.end_date:
        return contract.end_date
    ends = [p.end_date for p in members if p.end_date]
    return max(ends) if ends else None


def _invoiced_net(contract: Contract, invoices: List[Invoice]) -> Decimal:
    """Net amount invoiced on *contract*. A reminder repeats an invoice and adds nothing."""
    total = Decimal(0)
    for inv in invoices:
        if inv.cancelled or inv.is_reminder:
            continue
        if inv.contract is contract or (contract.id is not None and inv.contract_id == contract.id):
            total += inv.sum
    return total


def _hours_by_day(time_data: Optional[DataFrame], tags: set, units_per_workday: int) -> dict:
    """Calendar hours per date for events tagged with one of *tags*."""
    if time_data is None or time_data.empty:
        return {}
    rows = time_data[time_data["tag"].isin(tags)]
    if rows.empty:
        return {}
    hours = rows.apply(lambda row: event_hours(row, units_per_workday), axis=1)
    return hours.groupby(rows.index.date).sum().to_dict()


def _paced(
    contract: Contract,
    hours_by_day: dict,
    first: datetime.date,
    last: datetime.date,
    budget: Optional[float],
) -> list:
    """(start, end, amount) per week: the expected work the calendar does not already hold.

    Stops once *budget*, the agreed value not yet invoiced or planned, is used up.
    """
    unit_hours = contract.units_per_workday if contract.unit == TimeUnit.day else 1
    pace = contract.expected_units_per_week
    slices = []
    for week in pandas.period_range(first, last, freq="W"):
        start = max(first, week.start_time.date())
        end = min(last, week.end_time.date())
        days = (end - start).days + 1
        scheduled = sum(hours_by_day.get(start + datetime.timedelta(days=d), 0.0) for d in range(days)) / unit_hours
        amount = max(0.0, pace * days / 7 - scheduled) * float(contract.rate)
        if budget is not None:
            amount = min(amount, budget)
            budget -= amount
        if amount > 0:
            slices.append((start, end, amount))
        if budget is not None and budget <= 0:
            break
    return slices


def contracted_revenue(
    projects: List[Project],
    invoices: List[Invoice],
    time_data: Optional[DataFrame],
    until: datetime.date,
    currency: Optional[str] = None,
    today: Optional[datetime.date] = None,
) -> List[ContractedSlice]:
    """Revenue that committed contracts will still bring in beyond what is invoiced or planned.

    A contract counts once one of its projects is Upcoming or Active on the
    project board. What is left of its agreed value — the fixed price, or
    volume × rate — after invoices and after the tracked or scheduled work that
    shows as planned revenue is spread evenly over the rest of its term: until
    the contract's end date, else its projects'. Without an end date it falls
    on today. Once the term has ended, the contract adds nothing: whatever was
    not worked by then will not be.

    A contract with an expected workload follows that pace instead: each week,
    the expected hours the calendar does not already hold, until the end date,
    until the agreed volume runs out, or until *until*. Open-ended contracts
    without a pace have nothing to add to the calendar.

    Amounts are net and converted into *currency* at the current month's rate.
    """
    today = today or datetime.date.today()
    committed = _committed_contracts(projects, today)
    if not committed:
        return []

    # Planned revenue per project, so a contract's planned work is not counted twice.
    planned_by_project: dict = {}
    if time_data is not None and not time_data.empty:
        cal = revenue_from_calendar(
            time_data,
            projects,
            time_data.index.min().date(),
            time_data.index.max().date(),
            invoices=invoices,
            freq="Y",
        )
        if not cal.empty:
            planned_by_project = cal.groupby("project")["revenue"].sum().to_dict()

    slices = []
    for contract, members in committed:
        last = _term_end(contract, members)
        if last and last < today:
            continue
        agreed = contract.agreed_value
        paced = not contract.is_fixed_price and bool(contract.rate) and bool(contract.expected_units_per_week)
        if agreed is None and not paced:
            continue

        budget = None
        if agreed is not None:
            planned = sum(planned_by_project.get(p.title, 0.0) for p in members)
            budget = float(agreed - _invoiced_net(contract, invoices)) - planned
            if budget <= 0:
                continue

        fx = rate(contract.currency, currency, today) if currency and contract.currency else Decimal(1)
        if fx is None:
            continue

        first = max(today, contract.start_date)
        if paced:
            hours = _hours_by_day(time_data, {p.tag for p in members}, contract.units_per_workday)
            parts = _paced(contract, hours, first, min(last, until) if last else until, budget)
        else:
            parts = [(first, last if last and last >= first else first, budget)]

        slices.extend(ContractedSlice(contract, start, end, amount * float(fx)) for start, end, amount in parts)
    return slices


def spread(slices: List[ContractedSlice], freq: str, start: datetime.date, end: datetime.date) -> dict:
    """Total of *slices* per *freq* period between *start* and *end*, pro rata by day."""
    totals: dict = {}
    for s in slices:
        lo, hi = max(s.start, start), min(s.end, end)
        if lo > hi:
            continue
        days = (s.end - s.start).days + 1
        for period in pandas.period_range(lo, hi, freq=freq):
            a = max(lo, period.start_time.date())
            b = min(hi, period.end_time.date())
            totals[period] = totals.get(period, 0.0) + s.amount * ((b - a).days + 1) / days
    return totals


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
    """Received, invoiced, planned and contracted revenue per bucket for one chart window.

    Reconciles the revenue sources the dashboard chart needs into a single
    series so the frontend does not have to join them: invoices give
    ``received`` (paid) and ``invoiced`` (sent but unpaid) keyed by invoice
    date, the calendar gives ``planned`` — tracked or scheduled work that no
    timesheet has billed yet, in the past as well as the future — and
    committed contracts give ``contracted``, the agreed work not yet in the
    calendar (see :func:`contracted_revenue`).

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
        for contract, members in _committed_contracts(projects, today):
            end = _term_end(contract, members)
            if end:
                last_year = max(last_year, end.year)
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
            "contracted": 0.0,
            "invoice_count": 0,
            "hours": 0.0,
        }
        for p in periods
    }

    for inv in invoices:
        # A reminder chases an invoice that is already counted.
        if inv.cancelled or inv.is_reminder or not inv.date:
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

    cal = revenue_from_calendar(time_data, projects, window_start, window_end, invoices=invoices, freq=freq, currency=currency)
    if not cal.empty:
        grouped = cal.groupby("period").agg(revenue=("revenue", "sum"), hours=("hours", "sum")).reset_index()
        for _, row in grouped.iterrows():
            bucket = buckets.get(pandas.Period(row["period"], freq=freq))
            if bucket is None:
                continue
            bucket["planned"] += max(0.0, float(row["revenue"]))
            bucket["hours"] += float(row["hours"])

    contracted = contracted_revenue(projects, invoices, time_data, window_end, currency=currency, today=today)
    for period, amount in spread(contracted, freq, window_start, window_end).items():
        buckets[period]["contracted"] += amount

    current_period = pandas.Period(today, freq=freq)
    rows = []
    previous_year = None
    for period in periods:
        row = buckets[period]
        row["is_current"] = period == current_period
        row["is_future"] = period > current_period
        row["is_year_start"] = previous_year is not None and row["year"] != previous_year
        row["total"] = round(row["received"] + row["invoiced"] + row["planned"] + row["contracted"], 2)
        for key in ("received", "invoiced", "planned", "contracted", "hours"):
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


def cash_flow_series(
    invoices: List[Invoice],
    contracts: List[Contract],
    projects: List[Project],
    expenses: List[RecurringExpense],
    time_data: Optional[DataFrame],
    forecast_months: int = 6,
    country: str = "",
    today: Optional[datetime.date] = None,
) -> dict:
    """Project monthly cash inflows, expense outflows, and cumulative balance.

    Reconciles upcoming cash movements for a forward-looking forecast window:
    - Inflows from unpaid invoices (both draft and sent) placed in their effective due date bucket
      (overdue invoices map to the current month).
    - Inflows from planned calendar work shifted forward by contract payment terms
      (past un-invoiced work maps to the current month).
    - Inflows from contracted work (:func:`contracted_revenue`), shifted the same way.
    - Outflows from normalized fixed recurring expenses, rate-based contributions,
      and estimated income tax reserves.
    - Net flow and running cumulative balance across the forecast window.

    Empty buckets are included so the time axis stays continuous.
    """
    if forecast_months <= 0:
        forecast_months = 6

    today = today or datetime.date.today()
    forecast_start = today.replace(day=1)
    currency = primary_currency(country)

    periods = pandas.period_range(start=forecast_start, periods=forecast_months, freq="M")
    current_period = pandas.Period(today, freq="M")
    window_end = periods[-1].end_time.date()

    buckets = {
        p: {
            "month": p.start_time.date().isoformat(),
            "label": calendar.month_abbr[p.start_time.month],
            "year": p.start_time.year,
            "inflow_invoiced": 0.0,
            "inflow_planned": 0.0,
            "inflow_contracted": 0.0,
            "inflow_total": 0.0,
            "outflow": 0.0,
            "net": 0.0,
            "balance": 0.0,
            "is_current": p == current_period,
        }
        for p in periods
    }

    # 1. Inflows from unpaid invoices (both draft and sent)
    for inv in invoices:
        if inv.paid or inv.cancelled:
            continue
        converted = convert_invoice(inv, currency)
        if converted is None:
            continue
        # Use net basis: total minus VAT to align with net planned revenue
        net_amount = converted[0] - (converted[1] or Decimal(0))
        amount = float(net_amount)

        due_date = inv.effective_due_date
        if due_date is None:
            delay = inv.contract.term_of_payment if (inv.contract and inv.contract.term_of_payment is not None) else 31
            due_date = (inv.date + datetime.timedelta(days=delay)) if inv.date else today

        if isinstance(due_date, datetime.datetime):
            due_date = due_date.date()

        if due_date < today:
            target_bucket = buckets.get(current_period)
        else:
            inv_period = pandas.Period(due_date, freq="M")
            target_bucket = buckets.get(inv_period)

        if target_bucket is not None:
            target_bucket["inflow_invoiced"] += amount

    # 2. Inflows from planned calendar work shifted by contract payment terms
    if time_data is not None and not time_data.empty:
        contract_map = {c.id: c for c in contracts if c.id is not None}
        min_date = time_data.index.date.min()
        cal_start = min(forecast_start, min_date.replace(day=1))
        cal = monthly_revenue_from_calendar(time_data, projects, cal_start, window_end, invoices=invoices, currency=currency)
        if not cal.empty:
            for _, row in cal.iterrows():
                cid = row.get("contract_id")
                contract = contract_map.get(cid)
                payment_delay = contract.term_of_payment if (contract and contract.term_of_payment is not None) else 30
                work_month = row["month"]
                if isinstance(work_month, pandas.Timestamp):
                    work_month_date = work_month.date()
                elif isinstance(work_month, datetime.datetime):
                    work_month_date = work_month.date()
                else:
                    work_month_date = work_month
                work_month_start = work_month_date.replace(day=1)
                work_month_end = (work_month_start + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
                inflow_date = work_month_end + datetime.timedelta(days=payment_delay)
                inflow_period = pandas.Period(inflow_date, freq="M")
                if inflow_date < today or inflow_period < current_period:
                    target_bucket = buckets.get(current_period)
                else:
                    target_bucket = buckets.get(inflow_period)
                if target_bucket is not None:
                    target_bucket["inflow_planned"] += max(0.0, float(row["revenue"]))

    # 3. Inflows from contracted work, paid like planned work: payment terms after its month ends
    for s in contracted_revenue(projects, invoices, time_data, window_end, currency=currency, today=today):
        payment_delay = s.contract.term_of_payment if s.contract.term_of_payment is not None else 30
        for work_period, amount in spread([s], "M", forecast_start, window_end).items():
            inflow_date = work_period.end_time.date() + datetime.timedelta(days=payment_delay)
            target_bucket = buckets.get(max(pandas.Period(inflow_date, freq="M"), current_period))
            if target_bucket is not None:
                target_bucket["inflow_contracted"] += amount

    # 4. Outflows from normalized fixed recurring expenses, dynamic expenses, and tax reserves
    fixed_expenses = [e for e in expenses if e.rate is None and e.amount is not None]
    dynamic_expenses = [e for e in expenses if e.rate is not None]
    monthly_fixed = _monthly_expenses_total(fixed_expenses, currency)
    monthly_fixed_deductible = _monthly_expenses_total([e for e in fixed_expenses if e.tax_deductible], currency)

    # Precompute inflows and taxable profit base per bucket, and derive a single effective
    # tax rate from the window's annualized taxable income so uneven income is not taxed
    # at artificially high progressive brackets.
    month_data = {}
    total_tax_base = Decimal(0)
    for period in periods:
        row = buckets[period]
        row["inflow_invoiced"] = round(row["inflow_invoiced"], 2)
        row["inflow_planned"] = round(row["inflow_planned"], 2)
        row["inflow_contracted"] = round(row["inflow_contracted"], 2)
        row["inflow_total"] = round(row["inflow_invoiced"] + row["inflow_planned"] + row["inflow_contracted"], 2)

        month_inflow = Decimal(str(row["inflow_total"]))
        base_profit = max(Decimal(0), month_inflow - monthly_fixed_deductible)

        deductible_lines = _dynamic_lines(dynamic_expenses, base_profit, deductible=True)
        dyn_deductible = _lines_total(deductible_lines)

        month_tax_base = max(Decimal(0), base_profit - dyn_deductible)
        total_tax_base += month_tax_base
        month_data[period] = (month_tax_base, dyn_deductible)

    num_months = len(periods)
    if num_months > 0 and total_tax_base > 0:
        annual_tax_base = (total_tax_base / Decimal(num_months)) * Decimal(12)
        tax_res = compute_income_tax_reserve(annual_tax_base, country, year=forecast_start.year, currency=currency)
        effective_tax_rate = tax_res.effective_rate
    else:
        effective_tax_rate = Decimal(0)

    # 5. Net flow, cumulative balance, and summary totals
    running_balance = 0.0
    rows = []
    previous_year = None

    for period in periods:
        row = buckets[period]
        month_tax_base, dyn_deductible = month_data[period]

        monthly_tax = (month_tax_base * effective_tax_rate).quantize(Decimal("0.01"))
        post_tax = max(Decimal(0), month_tax_base - monthly_tax - (monthly_fixed - monthly_fixed_deductible))
        nondeductible_lines = _dynamic_lines(dynamic_expenses, post_tax, deductible=False)
        dyn_nondeductible = _lines_total(nondeductible_lines)

        total_outflow = monthly_fixed + dyn_deductible + monthly_tax + dyn_nondeductible
        row["outflow"] = round(float(total_outflow), 2)

        net = round(row["inflow_total"] - row["outflow"], 2)
        row["net"] = net
        running_balance = round(running_balance + net, 2)
        row["balance"] = running_balance
        row["is_year_start"] = previous_year is not None and row["year"] != previous_year
        previous_year = row["year"]
        rows.append(row)

    total_inflow = round(sum(r["inflow_total"] for r in rows), 2)
    total_outflow = round(sum(r["outflow"] for r in rows), 2)
    net_cash_flow = round(total_inflow - total_outflow, 2)

    return {
        "currency": currency,
        "window_start": forecast_start.isoformat(),
        "window_end": window_end.isoformat(),
        "buckets": rows,
        "total_inflow": total_inflow,
        "total_outflow": total_outflow,
        "net_cash_flow": net_cash_flow,
    }
