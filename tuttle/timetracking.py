from typing import Tuple, Union, Optional, List, Type

import datetime
from dataclasses import dataclass

import pandas
from pandas import DataFrame
from pandera import check_io
from pandera.typing import DataFrame

from tuttle.dev import deprecated

from . import schema
from .calendar import Calendar, ICloudCalendar, ICSCalendar
from .model import Project, Timesheet, TimeTrackingItem, User


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

    # convert period_start and period_end to strings that can be used as index for a DateTimeIndex
    period_start = period_start.strftime("%Y-%m-%d")
    period_end = period_end.strftime("%Y-%m-%d")

    tag_query = f"tag == '{project.tag}'"
    if period_end:
        ts_table = (
            timetracking_data.loc[period_start:period_end].query(tag_query).sort_index()
        )
        if ts_table.empty:
            raise ValueError(
                f"No time tracking data found for project {project.title} in period {period_start} - {period_end}"
            )
    else:
        ts_table = timetracking_data.loc[period_start].query(tag_query).sort_index()
    # convert all-day entries
    ts_table.loc[ts_table["all_day"], "duration"] = (
        project.contract.unit.to_timedelta() * project.contract.units_per_workday
    )
    if item_description:
        # TODO: extract item description from calendar
        ts_table["description"] = item_description

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
    if issubclass(type(cal), ICloudCalendar):
        timetracking_data = cal.to_data()
        return timetracking_data
    elif issubclass(type(cal), ICSCalendar):
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
    total_time = (
        time_tracking_data.filter(["tag", "duration"])
        .query(f"tag == @tag")
        .groupby("tag")
        .sum()
    )
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
    """Get time planning data from a source."""
    if from_date is None:
        from_date = datetime.date.today()
    if issubclass(type(source), Calendar):
        cal = source
        planning_data = cal.to_data()
    elif isinstance(source, pandas.DataFrame):
        planning_data = source
        schema.time_tracking.validate(planning_data)
    planning_data = planning_data[str(from_date) :]
    return planning_data
