"""Test calendar module."""

from pathlib import Path

from tuttle.calendar import FileCalendar


def test_file_calendar():
    """Test that the calendar object can be instantiated."""
    test_calendar_path = Path("tests/data/TuttleDemo-TimeTracking.ics")
    cal = FileCalendar(path=test_calendar_path, name="Test Calendar")
    assert cal is not None
