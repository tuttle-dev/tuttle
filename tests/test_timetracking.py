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
