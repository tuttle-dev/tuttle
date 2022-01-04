"""Test calendar module."""

from pathlib import Path

from tuttle.calendar import FileCalendar

def test_calendar_object():
    """Test that the calendar object can be instantiated."""
    test_calendar_path = Path("tests/data/test_calendar.ics")
    cal = FileCalendar(path=test_calendar_path, name="Test Calendar")