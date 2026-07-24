import datetime
from dataclasses import dataclass
from typing import List, Optional, Type, Union

import pandas
from pandera import check_io
from pandera.typing import DataFrame

from . import schema
from .calendar import Calendar, ICSCalendar
from .model import Project, Timesheet, TimeTrackingItem
from .time import TimeUnit

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
    return round(sum(sum_hours_by_tag(df, tag_to_workday).values()), 1)


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


def export_timesheet(
    timesheet: Timesheet,
    path: str,
):
    table = timesheet.table
    table = table.reset_index()
    table["date"] = table["date"].dt.strftime("%Y/%m/%d")
    table.loc["Total", :] = ("Total", table["hours"].sum(), "")
    table.to_excel(path, index=False)


# IMPORT


@check_io(out=schema.time_tracking)
def import_from_calendar(cal: Calendar) -> DataFrame:
    """Convert the raw calendar to time tracking data table."""
    if issubclass(type(cal), ICSCalendar):
        timetracking_data = cal.to_data()
        return timetracking_data
    else:
        raise NotImplementedError()


class TimetrackingSpreadsheetPreset:
    tag_col: str
    begin_col: Union[str, List[str]]
    end_col: Union[str, List[str]]
    duration_col: str
    title_col: str
    description_col: str


@dataclass
class TogglPreset(TimetrackingSpreadsheetPreset):
    tag_col = "Project"
    begin_col = ["Start date", "Start time"]
    end_col = ["End date", "End time"]
    duration_col = "Duration"
    title_col = "Task"
    description_col = "Description"
    all_day_col = None


def infer_spreadsheet_preset(data: DataFrame) -> Type[TimetrackingSpreadsheetPreset]:
    """Infer the spreadsheet preset from the columns of the dataframe."""
    raise NotImplementedError("TODO")


@check_io(
    out=schema.time_tracking,
)
def import_from_spreadsheet(
    path,
    preset: Optional[Type[TimetrackingSpreadsheetPreset]] = None,
    tag_col: Optional[str] = None,
    begin_col: Optional[Union[str, List[str]]] = None,
    end_col: Optional[Union[str, List[str]]] = None,
    duration_col: Optional[str] = None,
    title_col: Optional[str] = None,
    description_col: Optional[str] = None,
    all_day_col: Optional[str] = None,
) -> DataFrame:
    """Import time tracking data from a .csv file."""
    if preset:
        tag_col = preset.tag_col
        begin_col = preset.begin_col
        end_col = preset.end_col
        duration_col = preset.duration_col
        title_col = preset.title_col
        description_col = preset.description_col

    assert tag_col is not None
    assert begin_col is not None
    assert end_col is not None
    assert duration_col is not None

    raw_data = pandas.read_csv(
        path,
        engine="python",
        dtype={
            title_col: str,
        },
    )

    # combine date and time if separate
    if isinstance(begin_col, list):
        begin_date_col, begin_time_col = begin_col
        raw_data["begin"] = raw_data[begin_date_col] + " " + raw_data[begin_time_col]
        begin_col = "begin"
    if isinstance(end_col, list):
        end_date_col, end_time_col = end_col
        raw_data["end"] = raw_data[end_date_col] + " " + raw_data[end_time_col]
        end_col = "end"

    raw_data[begin_col] = pandas.to_datetime(raw_data[begin_col])
    raw_data[end_col] = pandas.to_datetime(raw_data[end_col])

    timetracking_data = raw_data.rename(
        columns={
            title_col: "title",
            tag_col: "tag",
            duration_col: "duration",
            description_col: "description",
            begin_col: "begin",
            end_col: "end",
        }
    )
    timetracking_data["duration"] = pandas.to_timedelta(timetracking_data["duration"])

    if title_col is None:
        timetracking_data["title"] = ""
    else:
        timetracking_data["title"] = timetracking_data["title"].fillna("")
    if begin_col is None:
        timetracking_data["begin"] = pandas.NaT
    if end_col is None:
        timetracking_data["end"] = pandas.NaT
    if description_col is None:
        timetracking_data["description"] = ""
    if all_day_col is None:
        timetracking_data["all_day"] = False

    timetracking_data = timetracking_data.set_index("begin")
    return timetracking_data


# ANALYSIS


def total_time_tracked(by: str) -> DataFrame:
    """Calculate the total time spent, grouped by project, client..."""
    if by == "project":
        raise NotImplementedError()
    elif by == "client":
        raise NotImplementedError()
    else:
        raise ValueError()


@check_io(
    time_tracking_data=schema.time_tracking,
)
def progress(
    project: Project,
    time_tracking_data: DataFrame,
):
    tag = project.tag
    total_time = time_tracking_data.filter(["tag", "duration"]).query("tag == @tag").groupby("tag").sum()
    # TODO: work with project.unit
    budget = project.contract.volume * datetime.timedelta(hours=1)
    return total_time.loc[tag]["duration"] / budget


@check_io(
    out=schema.time_planning,
)
def get_time_planning_data(
    source,
    from_date: datetime.date = None,
) -> DataFrame:
    """Get future calendar events as time planning data."""
    if from_date is None:
        from_date = datetime.date.today()
    if issubclass(type(source), Calendar):
        planning_data = source.to_data()
    elif isinstance(source, pandas.DataFrame):
        planning_data = source
        schema.time_tracking.validate(planning_data)
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")
    planning_data = planning_data[str(from_date) :]
    return planning_data


def get_tracked_data(
    source,
    until_date: datetime.date = None,
) -> DataFrame:
    """Get past calendar events (tracked time)."""
    if until_date is None:
        until_date = datetime.date.today()
    if issubclass(type(source), Calendar):
        data = source.to_data()
    elif isinstance(source, pandas.DataFrame):
        data = source
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")
    return data[: str(until_date)]


def get_planning_summary(
    source,
    projects: list,
) -> list:
    """Per-project aggregation of future planned hours with contract-derived revenue.

    Returns a list of dicts with: tag, title, planned_hours, planned_revenue,
    hours_budget, currency.
    """
    planning_data = get_time_planning_data(source)
    if planning_data.empty:
        return []

    tag_to_project = {p.tag: p for p in projects if p.tag}
    tag_to_workday = {p.tag: p.contract.units_per_workday for p in projects if p.tag and p.contract}
    planned_by_tag = sum_hours_by_tag(planning_data, tag_to_workday)

    results = []
    for tag, hours in sorted(planned_by_tag.items(), key=lambda x: -x[1]):
        project = tag_to_project.get(tag)
        contract = project.contract if project else None
        planned_revenue = 0.0
        hours_budget = None
        currency = "EUR"
        if contract:
            currency = contract.currency or "EUR"
            unit_hours = contract.units_per_workday if contract.unit == TimeUnit.day else 1
            billable_units = hours / unit_hours
            planned_revenue = float(billable_units * float(contract.rate))
            if contract.volume:
                hours_budget = float(contract.volume) * unit_hours

        results.append(
            {
                "tag": tag,
                "title": project.title if project else tag,
                "planned_hours": round(hours, 1),
                "planned_revenue": round(planned_revenue, 2),
                "hours_budget": hours_budget,
                "currency": currency,
            }
        )
    return results
