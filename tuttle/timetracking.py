from dataclasses import dataclass
import datetime
from tabnanny import check
from time import time

import pandas
from pandera import check_io
from pandera.typing import DataFrame


from . import schema
from .calendar import Calendar, ICloudCalendar, FileCalendar
from .model import (
    TimeTrackingItem,
    User,
    Project,
    Timesheet,
)


def generate_timesheet(
    source,
    project: Project,
    period: str,
    comment: str = None,
    group_by: str = None,
) -> Timesheet:
    # convert cal to data
    if issubclass(type(source), Calendar):
        cal = source
        timetracking_data = cal.to_data()
    ts_table = (
        timetracking_data.loc[period].query(f"tag == '{project.tag}'").sort_index()
    )

    if comment is None:
        comment = project.title
    ts = Timesheet(
        title=f"{project.title} {period}",
        period=period,
        project=project,
        comment=comment,
    )
    for record in ts_table.reset_index().to_dict("records"):
        ts.items.append(TimeTrackingItem(**record, timesheet=ts))

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
    elif issubclass(cal, FileCalendar):
        raise NotImplementedError()
    else:
        raise NotImplementedError()


@check_io(
    out=schema.time_tracking,
)
def import_from_csv(
    path,
    tag_col: str,
    duration_col: str,
    title_col: str = None,
    begin_col: str = None,
    end_col: str = None,
    description_col: str = None,
) -> DataFrame:
    """Import time tracking data from a .csv file."""
    raw_data = pandas.read_csv(
        path,
        engine="python",
    )
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
    if begin_col is None:
        timetracking_data["begin"] = pandas.NaT
    if end_col is None:
        timetracking_data["end"] = pandas.NaT
    if description_col is None:
        timetracking_data["description"] = ""

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
