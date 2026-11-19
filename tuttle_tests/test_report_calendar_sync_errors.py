"""A calendar that cannot be read reports why instead of looking empty.

Helper failures, missing permission and unreadable files used to come back as
an empty table: imports and syncs reported success, a failed import still
connected the calendar, and the UI never heard of it. The Swift helper is
replaced by a stub here; no test reads a real calendar.
"""

import base64

import pandas
import pytest

import tuttle.app.core.abstractions as abstractions
import tuttle.app.timetracking.data_source as data_source
import tuttle.app.timetracking.intent as timetracking_intent
import tuttle.app_db as app_db_mod
import tuttle.eventkit_bridge as eventkit_bridge
from tuttle.app.core.dispatch import _intents, dispatch
from tuttle.app.core.rpc_utils import reset_all
from tuttle.app.timetracking.data_source import calendar_cache_path

# Captured at import: the session-scoped rpc_env fixture in test_rpc_dispatch
# replaces AppDatabase.__init__ for the rest of the session.
_ORIGINAL_APP_DB_INIT = app_db_mod.AppDatabase.__init__

CALENDAR_ID = "work-calendar"
WORKSHOP = {
    "begin": "2026-09-15T07:00:00Z",
    "end": "2026-09-15T08:00:00Z",
    "title": "Workshop #heating",
    "description": "",
    "all_day": False,
    "duration_hours": 1.0,
}
LISTED = {"calendars": [{"id": CALENDAR_ID, "title": "Work", "source": "iCloud"}], "auth_status": "full_access"}
NO_ACCESS = "Tuttle has no access to your calendars. Allow it in System Settings, then try again."
UNREADABLE = "The calendar could not be read. Details are in the application log."
GONE = "This calendar no longer exists. Disconnect it and import another one."
KEPT = "Until a sync succeeds, Tuttle shows the events it had before."

# What the helper answers to "fetch-events" in each way it can fail.
FETCH_FAILURES = {
    "helper error": ({"error": "helper produced no output"}, UNREADABLE),
    "timeout": ({"error": "timeout"}, UNREADABLE),
    "invalid output": ({"error": "invalid helper output"}, UNREADABLE),
    "no event list": ({"auth_status": "full_access"}, UNREADABLE),
    "not a dict": (["unexpected"], UNREADABLE),
    "helper crashed": (RuntimeError("Failed to compile calendar helper"), UNREADABLE),
    "access denied": ({"events": [], "auth_status": "denied"}, NO_ACCESS),
    "access restricted": ({"events": [], "auth_status": "restricted"}, NO_ACCESS),
    "calendar gone": ({"events": [], "auth_status": "full_access"}, GONE),
}


def _ok(result: dict) -> dict:
    assert result["ok"] is True, f"RPC failed: {result.get('error')}"
    return result


def _helper(monkeypatch, fetch, listing=LISTED):
    """Stand in for the Swift helper; an exception as an answer is raised."""
    answers = {"fetch-events": fetch, "list-calendars": listing}

    def run(*args):
        answer = answers[args[0]]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(eventkit_bridge, "_run_helper", run)


@pytest.fixture
def user(tmp_path, monkeypatch):
    """A fresh user on a Mac, with no calendar connected yet."""

    def _patched_init(self, app_dir=None):
        _ORIGINAL_APP_DB_INIT(self, app_dir=tmp_path)

    monkeypatch.setattr(app_db_mod.AppDatabase, "__init__", _patched_init)
    monkeypatch.setattr(abstractions, "_active_db_path", tmp_path / "tuttle.db")
    monkeypatch.setattr(eventkit_bridge, "_IS_DARWIN", True)
    monkeypatch.setattr(timetracking_intent, "is_available", lambda: True)
    reset_all()
    _intents.clear()
    _ok(dispatch("db.ensure", {}))
    created = _ok(dispatch("users.create", {"params": {"name": "Harry Tuttle"}}))["data"]
    _ok(dispatch("users.switch", {"db_file": created["db_file"]}))
    try:
        yield
    finally:
        reset_all()
        _intents.clear()


def _connected() -> str:
    return _ok(dispatch("timetracking.get_source_config", {}))["data"]["source_type"]


def _titles() -> list:
    return [ev["title"] for ev in _ok(dispatch("timetracking.get_events", {}))["data"]]


@pytest.mark.parametrize("answer, message", FETCH_FAILURES.values(), ids=FETCH_FAILURES.keys())
def test_a_failed_import_says_why_and_connects_nothing(user, monkeypatch, answer, message):
    _helper(monkeypatch, fetch=answer, listing={"calendars": [], "auth_status": "full_access"})

    result = dispatch("timetracking.import_system_calendar", {"calendar_id": CALENDAR_ID})

    assert (result["ok"], result["error"]) == (False, message)
    assert _connected() == ""
    assert _titles() == []


def test_an_empty_calendar_imports_nothing_without_an_error(user, monkeypatch):
    _helper(monkeypatch, fetch={"events": [], "auth_status": "full_access"})

    result = _ok(dispatch("timetracking.import_system_calendar", {"calendar_id": CALENDAR_ID}))

    assert result["data"]["imported_count"] == 0
    assert _connected() == ""


@pytest.mark.parametrize("answer, message", FETCH_FAILURES.values(), ids=FETCH_FAILURES.keys())
def test_a_failed_sync_keeps_the_events_and_says_so(user, monkeypatch, answer, message):
    _helper(monkeypatch, fetch={"events": [WORKSHOP], "auth_status": "full_access"})
    _ok(dispatch("timetracking.import_system_calendar", {"calendar_id": CALENDAR_ID}))
    _helper(monkeypatch, fetch=answer, listing={"calendars": [], "auth_status": "full_access"})

    for method in ("timetracking.sync", "timetracking.restore"):
        result = dispatch(method, {})
        assert (result["ok"], result["error"]) == (False, f"{message} {KEPT}")

    assert _connected() == "system"
    assert _titles() == ["Workshop #heating"]
    assert list(pandas.read_parquet(calendar_cache_path())["title"]) == ["Workshop #heating"]


def test_a_failed_restore_without_earlier_events_names_only_the_problem(user, monkeypatch):
    _helper(monkeypatch, fetch={"events": [WORKSHOP], "auth_status": "full_access"})
    _ok(dispatch("timetracking.import_system_calendar", {"calendar_id": CALENDAR_ID}))
    calendar_cache_path().unlink()
    reset_all()
    _helper(monkeypatch, fetch={"events": [], "auth_status": "denied"})

    result = dispatch("timetracking.restore", {})

    assert (result["ok"], result["error"]) == (False, NO_ACCESS)


def test_events_that_cannot_be_saved_are_reported(user, monkeypatch):
    def disk_full(*args):
        raise OSError("No space left on device")

    monkeypatch.setattr(data_source, "write_calendar_cache", disk_full)
    _helper(monkeypatch, fetch={"events": [WORKSHOP], "auth_status": "full_access"})

    imported = _ok(dispatch("timetracking.import_system_calendar", {"calendar_id": CALENDAR_ID}))
    synced = _ok(dispatch("timetracking.sync", {}))

    for result in (imported, synced):
        assert "could not be saved" in result["warning"]
        assert "application log" in result["warning"]
    assert _titles() == ["Workshop #heating"]


def test_listing_calendars_reports_a_failing_helper(user, monkeypatch):
    _helper(monkeypatch, fetch=None, listing={"error": "timeout"})

    result = dispatch("timetracking.list_system_calendars", {})

    assert (result["ok"], result["error"]) == (False, UNREADABLE)


def _ics(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def test_an_unreadable_ics_file_says_so_and_connects_nothing(user):
    result = dispatch("timetracking.import_ics", {"content": _ics("not a calendar"), "name": "work.ics"})

    assert result["ok"] is False
    assert result["error"] == (
        "work.ics could not be read as a calendar. Export the calendar again as an .ics file and import that."
    )
    assert _connected() == ""


def test_an_ics_file_without_events_imports_nothing(user):
    empty = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Tuttle//Test//EN\nEND:VCALENDAR\n"

    result = _ok(dispatch("timetracking.import_ics", {"content": _ics(empty), "name": "empty.ics"}))

    assert result["data"]["imported_count"] == 0
    assert _connected() == ""
