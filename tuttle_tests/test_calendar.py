"""Test calendar module."""

from pathlib import Path

from tuttle.calendar import ICSCalendar, extract_hashtag


def test_file_calendar():
    """Test that the calendar object can be instantiated."""
    test_calendar_path = Path("tuttle_tests/data/TuttleDemo-TimeTracking.ics")
    cal = ICSCalendar(path=test_calendar_path, name="Test Calendar")
    assert cal is not None


def test_extract_hashtag():
    assert extract_hashtag("#hashtag string") == "#hashtag"
    assert extract_hashtag("no hashtags") == ""
