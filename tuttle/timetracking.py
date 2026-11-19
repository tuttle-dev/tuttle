import datetime
from typing import List

from pandera.typing import DataFrame

from .model import Invoice, Project, Timesheet, TimeTrackingItem

DEFAULT_WORKDAY_HOURS = 8


def event_hours(row, units_per_workday: int = DEFAULT_WORKDAY_HOURS) -> float:
    """Hours credited for a calendar row; all-day counts as one workday."""
    if bool(row.get("all_day", False)):
        return float(units_per_workday)
    dur = row.get("duration")
    if dur is None or not hasattr(dur, "total_seconds"):
        return 0.0
    return dur.total_seconds() / 3600


def sum_hours_by_tag(
    df: DataFrame,
    tag_to_workday: dict | None = None,
) -> dict[str, float]:
    """Sum effective hours grouped by project tag."""
    tag_to_workday = tag_to_workday or {}
    totals: dict[str, float] = {}
    for _, row in df.iterrows():
        tag = str(row.get("tag", ""))
        workday = tag_to_workday.get(tag, DEFAULT_WORKDAY_HOURS)
        totals[tag] = totals.get(tag, 0.0) + event_hours(row, workday)
    return totals


def total_event_hours(df: DataFrame, tag_to_workday: dict | None = None) -> float:
    """Sum effective hours across all rows."""
    return round(sum(sum_hours_by_tag(df, tag_to_workday).values()), 2)


def invoiced_ranges_by_tag(invoices: List[Invoice]) -> dict:
    """Map project tag -> list of (period_start, period_end) already invoiced.

    A timesheet's period is the exact slice of calendar hours that were
    pulled into an invoice, regardless of the invoice's own date (an
    invoice raised in August can cover a timesheet for July). Cancelled
    invoices and drafts don't count: their hours are still un-invoiced.
    """
    ranges: dict = {}
    for inv in invoices:
        if not inv.is_counted:
            continue
        for ts in inv.timesheets:
            tag = ts.project.tag if ts.project else None
            if not tag:
                continue
            ranges.setdefault(tag, []).append((ts.period_start, ts.period_end))
    return ranges


def drop_invoiced(time_data: DataFrame, invoices: List[Invoice]) -> DataFrame:
    """Calendar rows that no timesheet of an issued, non-cancelled invoice covers yet."""
    invoiced_ranges = invoiced_ranges_by_tag(invoices)
    if not invoiced_ranges:
        return time_data
    already_invoiced = [
        any(start <= d <= end for start, end in invoiced_ranges.get(tag, ()))
        for d, tag in zip(time_data.index.date, time_data["tag"])
    ]
    return time_data[[not v for v in already_invoiced]]


def drop_completed(time_data: DataFrame, projects: List[Project]) -> DataFrame:
    """Calendar rows of projects not completed yet.

    A completed project is invoiced and paid in full, even where its
    invoices carry no timesheet, such as invoices imported from elsewhere.
    """
    completed = {p.tag for p in projects if p.board_stage() == "Completed"}
    if not completed:
        return time_data
    return time_data[~time_data["tag"].isin(completed)]


def generate_timesheet(
    timetracking_data: DataFrame,
    project: Project,
    period_start: datetime.date,
    period_end: datetime.date,
    date: datetime.date = datetime.date.today(),
    comment: str = "",
    item_description: str = None,
) -> Timesheet:
    """Create a timesheet from a dataframe of time tracking data."""

    tag_query = f"tag == '{project.tag}'"
    timetracking_data = timetracking_data.sort_index()

    # Compare on local dates extracted from the (possibly tz-aware) index so that
    # an event at 2022-01-31 23:00 UTC -> 2022-02-01 00:00 CET lands in February,
    # matching what the user sees in their calendar app.
    index_dates = timetracking_data.index.date
    if period_end:
        mask = (index_dates >= period_start) & (index_dates <= period_end)
        ts_table = timetracking_data[mask].query(tag_query).sort_index()
        if ts_table.empty:
            raise ValueError(
                f"No time tracking data found for project {project.title} in period {period_start} - {period_end}"
            )
    else:
        mask = index_dates == period_start
        ts_table = timetracking_data[mask].query(tag_query).sort_index()

    # All-day events represent one workday of effort, independent of contract.unit.
    # units_per_workday is documented as hours per workday, so always expand to hours.
    workday = datetime.timedelta(hours=1) * project.contract.units_per_workday
    ts_table.loc[ts_table["all_day"], "duration"] = workday
    if item_description:
        # Only fill rows that have no per-event description from the calendar source.
        mask = ts_table["description"].isna() | (ts_table["description"] == "")
        ts_table.loc[mask, "description"] = item_description

    period_str = f"{period_start} - {period_end}"
    ts = Timesheet(
        title=f"{project.title} - {period_str}",
        period_start=period_start,
        period_end=period_end,
        project=project,
        comment=comment,
        date=date,
    )
    for record in ts_table.reset_index().to_dict("records"):
        ts.items.append(TimeTrackingItem(**record))

    return ts


# IMPORT
