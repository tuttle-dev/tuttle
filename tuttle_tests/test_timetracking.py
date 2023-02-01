"""Test timetracking module"""
from time import time
import pandas
import datetime

from tuttle import timetracking


def test_timetracking_import_toggl():
    """Test import of time tracking data from csv exported by Toggl."""
    data = timetracking.import_from_spreadsheet(
        path="tuttle_tests/data/test_time_tracking_toggl.csv",
        preset=timetracking.TogglPreset,
    )
    assert not data.empty

    pass


def test_calendar_to_data(demo_calendar_timetracking):
    time_tracking_data = demo_calendar_timetracking.to_data()
    assert not time_tracking_data.empty


def test_generate_timesheet_from_demo_calendar(
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


def test_create_timesheet(
    demo_projects,
):
    # create synthetic time tracking data
    data = {
        "begin": ["01-01-2022 08:00:00", "01-02-2022 08:00:00"],
        "end": ["01-01-2022 12:00:00", "01-02-2022 12:00:00"],
        "title": ["Task 1", "Task 2"],
        "tag": ["#HeatingEngineering", "#HeatingEngineering"],
        "description": ["Work on task 1", "Work on task 2"],
        "all_day": [False, False],
    }
    timetracking_data = pandas.DataFrame(data)
    timetracking_data["begin"] = pandas.to_datetime(
        timetracking_data["begin"], format="%m-%d-%Y %H:%M:%S"
    )
    timetracking_data["end"] = pandas.to_datetime(
        timetracking_data["end"], format="%m-%d-%Y %H:%M:%S"
    )
    timetracking_data["duration"] = (
        timetracking_data["end"] - timetracking_data["begin"]
    )
    timetracking_data = timetracking_data.set_index("begin")

    assert timetracking_data["duration"].sum() == pandas.Timedelta("8 hours")

    project = demo_projects[0]

    # create a timesheet
    period_start = datetime.date(2022, 1, 1)
    period_end = datetime.date(2022, 12, 31)
    timesheet = timetracking.generate_timesheet(
        timetracking_data, project, period_start, period_end
    )

    # test timesheet properties
    assert timesheet.project.title == "Heating Engineering"
    assert timesheet.comment == ""
    assert timesheet.date == datetime.date.today()
    assert timesheet.total == datetime.timedelta(hours=8)
    assert timesheet.empty == False
