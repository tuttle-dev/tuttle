"""Test timetracking module"""
import pandas

from tuttle import timetracking


def test_timetracking_import_csv():
    """Test import of time tracking data from csv."""
    data = timetracking.import_from_csv(
        path="tests/data/test_time_tracking_toggl.csv",
        tag_col="Client",
        duration_col="Duration",
        description_col="Description",
    )
    assert not data.empty


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
                period=period,
                item_description=project.title,
            )
            assert (timesheet.empty) or (timesheet.total >= pandas.Timedelta("0 hours"))
