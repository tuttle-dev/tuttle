"""Time tracking — import functions delegated to calendula."""

import datetime

from pandas import DataFrame
from pandera import check_io
from pandera.typing import DataFrame

from . import schema
from .model import Project, Timesheet, TimeTrackingItem

# --- Delegated to calendula ---

from calendula.timetracking import (
    import_from_calendar,
    import_from_spreadsheet,
    get_time_planning_data,
    TimetrackingSpreadsheetPreset,
    TogglPreset,
)

# --- Tuttle-specific (coupled to tuttle's model layer) ---


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

    # string keys for pandas DatetimeIndex slicing
    start_key = period_start.strftime("%Y-%m-%d")
    end_key = period_end.strftime("%Y-%m-%d")

    tag_query = f"tag == '{project.tag}'"
    timetracking_data = timetracking_data.sort_index()
    if period_end:
        ts_table = (
            timetracking_data.loc[start_key:end_key].query(tag_query).sort_index()
        )
        if ts_table.empty:
            raise ValueError(
                f"No time tracking data found for project {project.title} in period {start_key} - {end_key}"
            )
    else:
        ts_table = timetracking_data.loc[start_key].query(tag_query).sort_index()
    # convert all-day entries
    ts_table.loc[ts_table["all_day"], "duration"] = (
        project.contract.unit.to_timedelta() * project.contract.units_per_workday
    )
    if item_description:
        ts_table["description"] = item_description

    period_str = f"{start_key} - {end_key}"
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
    budget = project.contract.volume * datetime.timedelta(hours=1)
    return total_time.loc[tag]["duration"] / budget
