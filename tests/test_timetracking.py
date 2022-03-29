"""Test timetracking module"""
from time import time
import pandas

from tuttle import timetracking


def test_timetracking_import_toggl():
    """Test import of time tracking data from csv exported by Toggl."""
    data = timetracking.import_from_spreadsheet(
        path="tests/data/test_time_tracking_toggl.csv",
        preset=timetracking.TimetrackingSpreadsheetPreset.Toggl,
    )
    assert not data.empty

    pass


def test_calendar_to_data(demo_calendar_timetracking):
    time_tracking_data = demo_calendar_timetracking.to_data()
    assert not time_tracking_data.empty


def test_generate_timesheet(
    demo_projects,
    demo_calendar_timetracking,
):
    for period in ["January 2022", "February 2022"]:
        for project in demo_projects:
            timesheet = timetracking.generate_timesheet(
                source=demo_calendar_timetracking,
                project=project,
                period_start=period,
                item_description=project.title,
            )
            assert (timesheet.empty) or (timesheet.total >= pandas.Timedelta("0 hours"))
