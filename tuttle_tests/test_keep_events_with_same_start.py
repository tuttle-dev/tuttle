"""Calendar events that start at the same time are all kept.

Merging calendar rows used to deduplicate on start time alone, so of two
different events starting at the same minute only one survived a re-import,
an import of a second calendar, or the merge with manual entries. Its hours
were missing from timesheets, invoices and Planned.
"""

import pandas
import pytest

import tuttle.app.timetracking.data_source as data_source
from tuttle.app.timetracking.aggregation import merge_dataframes
from tuttle.app.timetracking.data_source import TimeTrackingDataFrameSource
from tuttle.calendar import ICSCalendar
from tuttle.timetracking import total_event_hours

WORK_CALENDAR = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Tuttle//Test//EN
BEGIN:VEVENT
UID:workshop@example.com
DTSTART:20260915T070000Z
DTEND:20260915T080000Z
SUMMARY:Workshop #heating
END:VEVENT
BEGIN:VEVENT
UID:review@example.com
DTSTART:20260915T070000Z
DTEND:20260915T093000Z
SUMMARY:Design review #cooling
END:VEVENT
BEGIN:VEVENT
UID:offsite@example.com
DTSTART;VALUE=DATE:20260917
DTEND;VALUE=DATE:20260919
SUMMARY:Offsite #heating
END:VEVENT
BEGIN:VEVENT
UID:holiday@example.com
DTSTART;VALUE=DATE:20260917
DTEND;VALUE=DATE:20260918
SUMMARY:Public holiday
END:VEVENT
END:VCALENDAR
"""


def _calendar(text: str = WORK_CALENDAR) -> pandas.DataFrame:
    df = ICSCalendar(name="work.ics", content=text.encode()).to_data()
    return df.assign(source="calendar")


def _event(start: str, hours: float, title: str, tag: str) -> pandas.DataFrame:
    begin = pandas.Timestamp(start, tz="CET")
    return pandas.DataFrame(
        [
            {
                "title": title,
                "tag": tag,
                "description": "",
                "duration": pandas.Timedelta(hours=hours),
                "all_day": False,
                "end": begin + pandas.Timedelta(hours=hours),
                "source": "calendar",
            }
        ],
        index=pandas.DatetimeIndex([begin], name="begin"),
    )


def _manual(*events: pandas.DataFrame) -> pandas.DataFrame:
    """Manual entries as the database hands them over, each with its own id."""
    df = pandas.concat(events)
    return df.assign(source="manual", entry_id=range(1, len(df) + 1), duration_only=False)


def _titles(df: pandas.DataFrame) -> list:
    return sorted(df["title"].fillna(""))


def test_a_second_calendar_keeps_the_events_of_the_first():
    first = _event("2026-09-15T09:00", 1, "Workshop #heating", "#heating")
    second = _event("2026-09-15T09:00", 2.5, "Design review #cooling", "#cooling")

    merged = merge_dataframes(first, second)

    assert _titles(merged) == ["Design review #cooling", "Workshop #heating"]
    assert total_event_hours(merged) == 3.5


def test_events_with_the_same_start_in_one_import_all_stay():
    existing = _event("2026-09-01T09:00", 1, "Kickoff #heating", "#heating")

    merged = merge_dataframes(existing, _calendar())

    assert len(merged) == 1 + 5  # the two-day offsite is one row per day
    assert _titles(merged).count("Offsite #heating") == 2
    assert {"Workshop #heating", "Design review #cooling", "Public holiday"} <= set(merged["title"])


def test_reimporting_a_calendar_adds_nothing(tmp_path):
    """The earlier import comes back from the on-disk cache, the new one from the file."""
    cache = tmp_path / "events.parquet"
    merge_dataframes(None, _calendar()).to_parquet(cache)
    cached = pandas.read_parquet(cache)

    merged = merge_dataframes(cached, _calendar())

    assert _titles(merged) == _titles(_calendar())
    assert total_event_hours(merged) == total_event_hours(_calendar())


def test_an_edited_event_does_not_replace_its_old_copy():
    """Neither calendar source gives Tuttle an event id, so a changed event is a new one."""
    original = _event("2026-09-15T09:00", 1, "Workshop #heating", "#heating")
    longer = _event("2026-09-15T09:00", 2, "Workshop #heating", "#heating")
    renamed = _event("2026-09-15T09:00", 1, "Workshop part 1 #heating", "#heating")

    assert len(merge_dataframes(original, longer)) == 2
    assert len(merge_dataframes(original, renamed)) == 2


def test_manual_entries_are_never_dropped():
    calendar = _event("2026-09-15T09:00", 1, "Workshop #heating", "#heating")
    manual = _manual(
        _event("2026-09-15T09:00", 1, "Workshop #heating", "#heating"),
        _event("2026-09-16T00:00", 2, "", "#heating"),
        _event("2026-09-16T00:00", 2, "", "#heating"),
    )

    merged = merge_dataframes(calendar, manual)

    assert sorted(merged["source"]) == ["calendar", "manual", "manual", "manual"]


@pytest.fixture
def frame_source():
    ds = TimeTrackingDataFrameSource()
    ds.clear()
    yield ds
    ds.clear()


def test_logging_time_keeps_calendar_events_with_the_same_start(frame_source, monkeypatch):
    """Any manual entry made the calendar rows go through the merge, which collapsed them."""
    manual = _manual(_event("2026-09-20T00:00", 1, "", "#heating"))
    monkeypatch.setattr(data_source.ManualEntriesDataSource, "load_frame", lambda self: manual)
    frame_source.store_data_frame(_calendar())

    df = frame_source.get_data_frame()

    assert len(df) == len(_calendar()) + 1
    assert {"Workshop #heating", "Design review #cooling"} <= set(df["title"])
