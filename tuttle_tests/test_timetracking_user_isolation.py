"""One user's calendar, timer and cache must never reach another user.

Regression tests for a leak where the calendar connection, the running timer
and the calendar cache were stored app-wide: after switching to the demo user,
Time Tracking showed the real user's calendar events.
"""

from pathlib import Path

import pandas
import pytest

import tuttle.app.core.abstractions as abstractions
import tuttle.app.timetracking.intent as timetracking_intent
import tuttle.app_db as app_db_mod
from tuttle.app.core.dispatch import _intents, dispatch
from tuttle.app.core.rpc_utils import reset_all
from tuttle.app.timetracking.data_source import calendar_cache_path, user_cache_dir
from tuttle.app_db import AppDatabase

DEMO = "harry-tuttle.db"
SECRET_TAG = "#secretclient"

# Captured at import: the session-scoped rpc_env fixture in test_rpc_dispatch
# replaces AppDatabase.__init__ for the rest of the session.
_ORIGINAL_APP_DB_INIT = app_db_mod.AppDatabase.__init__


def _ok(result: dict) -> dict:
    assert result["ok"] is True, f"RPC failed: {result.get('error')}"
    return result["data"]


def _secret_calendar() -> pandas.DataFrame:
    begin = pandas.Timestamp("2026-09-16T09:00", tz="CET")
    return pandas.DataFrame(
        [
            {
                "title": f"Confidential meeting {SECRET_TAG}",
                "tag": SECRET_TAG,
                "description": "",
                "duration": pandas.Timedelta(hours=2),
                "all_day": False,
                "end": begin + pandas.Timedelta(hours=2),
            }
        ],
        index=pandas.DatetimeIndex([begin], name="begin"),
    )


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    """A fresh app dir with a real user who has a connected system calendar, plus the demo user."""

    def _patched_init(self, app_dir=None):
        _ORIGINAL_APP_DB_INIT(self, app_dir=tmp_path)

    monkeypatch.setattr(app_db_mod.AppDatabase, "__init__", _patched_init)
    monkeypatch.setattr(abstractions, "_active_db_path", tmp_path / "tuttle.db")
    monkeypatch.setattr(timetracking_intent, "is_available", lambda: True)
    monkeypatch.setattr(timetracking_intent, "fetch_events", lambda *a, **kw: _secret_calendar())
    reset_all()
    _intents.clear()

    _ok(dispatch("db.ensure", {}))
    real = _ok(dispatch("users.create", {"params": {"name": "Real Freelancer"}}))
    _ok(dispatch("users.switch", {"db_file": real["db_file"]}))
    _ok(dispatch("timetracking.import_system_calendar", {"calendar_id": "private-calendar"}))
    _ok(dispatch("timetracking.start_timer", {"tag": SECRET_TAG, "title": "Secret work"}))
    try:
        yield tmp_path, real["db_file"]
    finally:
        reset_all()
        _intents.clear()


def _events() -> list:
    _ok(dispatch("timetracking.restore", {}))
    return _ok(dispatch("timetracking.get_events", {}))


def test_demo_user_never_sees_the_real_users_calendar_or_timer(app_env):
    _ok(dispatch("users.ensure_demo", {}))
    _ok(dispatch("users.switch", {"db_file": DEMO}))

    assert all(ev["tag"] != SECRET_TAG for ev in _events())
    assert _ok(dispatch("timetracking.get_source_config", {}))["source_type"] == "demo"
    assert _ok(dispatch("timetracking.get_timer_state", {}))["running"] is False
    cached = pandas.read_parquet(calendar_cache_path(abstractions.get_active_db()))
    assert SECRET_TAG not in set(cached["tag"])


def test_switching_back_restores_the_real_users_own_state(app_env):
    _, real_db = app_env
    _ok(dispatch("users.ensure_demo", {}))
    _ok(dispatch("users.switch", {"db_file": DEMO}))
    _ok(dispatch("users.switch", {"db_file": real_db}))

    assert _ok(dispatch("timetracking.get_source_config", {}))["source_type"] == "system"
    timer = _ok(dispatch("timetracking.get_timer_state", {}))
    assert timer["running"] is True
    assert timer["tag"] == SECRET_TAG


def test_installing_the_demo_leaves_the_active_user_untouched(app_env):
    # The demo is installed while the real user is still active.
    _ok(dispatch("users.ensure_demo", {}))

    assert _ok(dispatch("timetracking.get_source_config", {}))["source_type"] == "system"
    tags = {ev["tag"] for ev in _ok(dispatch("timetracking.get_events", {}))}
    assert tags == {SECRET_TAG}


def test_deleting_a_user_deletes_their_calendar_cache(app_env):
    tmp, real_db = app_env
    _ok(dispatch("users.ensure_demo", {}))
    _ok(dispatch("users.switch", {"db_file": DEMO}))
    cache_dir = user_cache_dir(tmp / real_db)
    assert cache_dir.exists()

    _ok(dispatch("users.delete", {"db_file": real_db}))
    assert not cache_dir.exists()


def test_shared_state_from_older_versions_is_deleted_with_a_notice(tmp_path):
    app_db = AppDatabase.__new__(AppDatabase)
    _ORIGINAL_APP_DB_INIT(app_db, app_dir=tmp_path)
    app_db.set_setting("timetracking.source_type", "system")
    app_db.set_setting("timetracking.calendar_id", "private-calendar")
    app_db.set_setting("timetracking.timer_start", "2026-09-25T08:00:00+00:00")
    app_db.set_setting("timetracking.timer_tag", SECRET_TAG)
    legacy = [tmp_path / "cache" / "timetracking_events.parquet", tmp_path / "cache" / "timetracking_events.pkl"]
    legacy[0].parent.mkdir()
    for path in legacy:
        path.write_bytes(b"real events")

    notices = app_db.drop_shared_timetracking_state()

    assert any("connect your calendar again" in n for n in notices)
    assert any("timer" in n and "add it as an entry" in n for n in notices)
    assert app_db.get_all_settings(prefix="timetracking.") == {}
    assert not any(path.exists() for path in legacy)
    assert app_db.drop_shared_timetracking_state() == []


def test_leftover_demo_state_is_deleted_without_a_notice(tmp_path):
    app_db = AppDatabase.__new__(AppDatabase)
    _ORIGINAL_APP_DB_INIT(app_db, app_dir=tmp_path)
    app_db.set_setting("timetracking.source_type", "demo")

    assert app_db.drop_shared_timetracking_state() == []
    assert app_db.get_all_settings(prefix="timetracking.") == {}


def test_demo_user_from_an_older_version_gets_its_calendar_back(app_env):
    # Before per-user caches, the demo calendar lived only in the shared file.
    tmp, _ = app_env
    _ok(dispatch("users.ensure_demo", {}))
    calendar_cache_path(Path(tmp / DEMO)).unlink()

    _ok(dispatch("users.switch", {"db_file": DEMO}))

    assert calendar_cache_path(Path(tmp / DEMO)).exists()
    assert _events()
