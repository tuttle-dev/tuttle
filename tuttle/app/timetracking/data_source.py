from pathlib import Path
from typing import Optional

import pandas
import sqlmodel
from loguru import logger
from pandas import DataFrame

from ... import timetracking
from ...app_db import AppDatabase
from ...calendar import ICSCalendar
from ...data_dir import get_data_dir
from ...dev import singleton
from ...model import TimeTrackingItem
from ..core.abstractions import SQLModelDataSourceMixin
from ..core.rpc_utils import register_reset
from .aggregation import merge_dataframes

_SETTING_SOURCE_TYPE = "timetracking.source_type"
_SETTING_CALENDAR_ID = "timetracking.calendar_id"
_SETTING_CALENDAR_NAME = "timetracking.calendar_name"

_SETTING_TIMER_START = "timetracking.timer_start"
_SETTING_TIMER_TAG = "timetracking.timer_tag"
_SETTING_TIMER_TITLE = "timetracking.timer_title"

TZ = "CET"


def to_cet(dt) -> pandas.Timestamp:
    # Calendar sources index events in CET; a row in another zone (or naive)
    # makes pandas degrade the whole index to dtype object, breaking `.date`.
    ts = pandas.Timestamp(dt)
    return ts.tz_convert(TZ) if ts.tzinfo else ts.tz_localize(TZ)


def _naive_cet(dt):
    # SQLite drops tzinfo, so rows are stored as CET wall-clock time.
    return to_cet(dt).tz_localize(None).to_pydatetime()


def _cache_path() -> Path:
    d = get_data_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d / "timetracking_events.parquet"


@singleton
class TimeTrackingDataFrameSource:
    """The in-memory time-tracking frame: calendar rows plus manual entries.

    Calendar rows come from the connected source (and its on-disk cache).
    Manual entries are ``TimeTrackingItem`` rows without a timesheet and are
    merged in from the database on the next read after anything replaced the
    frame. Because this is a @singleton, its data survives intent resets; the
    registered reset callback clears it when switching users.
    """

    def __init__(self):
        super().__init__()
        self.data: Optional[DataFrame] = None
        self._manual_loaded = False
        register_reset(self.clear)

    def get_data_frame(self) -> Optional[DataFrame]:
        if not self._manual_loaded:
            self.refresh_manual_rows()
        return self.data

    def store_data_frame(self, data: Optional[DataFrame]):
        """Replace the calendar rows; manual entries are re-attached on the next read."""
        self.data = data
        self._manual_loaded = False

    def calendar_rows(self) -> Optional[DataFrame]:
        df = self.data
        if df is None or df.empty:
            return None
        if "source" in df.columns:
            df = df[df["source"] != "manual"]
        return df if not df.empty else None

    def has_calendar_rows(self) -> bool:
        return self.calendar_rows() is not None

    def refresh_manual_rows(self):
        calendar = self.calendar_rows()
        manual = ManualEntriesDataSource().load_frame()
        self.data = merge_dataframes(calendar, manual) if manual is not None else calendar
        self._manual_loaded = True

    def clear(self):
        self.data = None
        self._manual_loaded = False

    # -- persistence helpers ---------------------------------------------------

    def save_to_cache(self):
        calendar = self.calendar_rows()
        if calendar is None:
            return
        path = _cache_path()
        try:
            calendar.to_parquet(path)
            logger.info(f"Persisted {len(calendar)} calendar events to {path}")
        except Exception as ex:
            logger.warning(f"Failed to persist time-tracking cache: {ex}")

    def load_from_cache(self) -> bool:
        path = _cache_path()
        if not path.exists():
            return False
        try:
            df = pandas.read_parquet(path)
            if "source" not in df.columns:
                df["source"] = "calendar"
            self.store_data_frame(df)
            logger.info(f"Restored {len(df)} calendar events from cache")
            return True
        except Exception as ex:
            logger.warning(f"Failed to load time-tracking cache: {ex}")
            return False

    def clear_cache(self):
        path = _cache_path()
        if path.exists():
            path.unlink()

    @staticmethod
    def save_source_config(source_type: str, calendar_id: str = "", calendar_name: str = ""):
        db = AppDatabase()
        db.set_setting(_SETTING_SOURCE_TYPE, source_type)
        db.set_setting(_SETTING_CALENDAR_ID, calendar_id)
        db.set_setting(_SETTING_CALENDAR_NAME, calendar_name)

    @staticmethod
    def get_source_config() -> dict:
        db = AppDatabase()
        return {
            "source_type": db.get_setting(_SETTING_SOURCE_TYPE) or "",
            "calendar_id": db.get_setting(_SETTING_CALENDAR_ID) or "",
            "calendar_name": db.get_setting(_SETTING_CALENDAR_NAME) or "",
        }

    @staticmethod
    def clear_source_config():
        db = AppDatabase()
        for key in (_SETTING_SOURCE_TYPE, _SETTING_CALENDAR_ID, _SETTING_CALENDAR_NAME):
            db.delete_setting(key)

    # -- timer state -----------------------------------------------------------

    @staticmethod
    def save_timer_state(start_iso: str, tag: str = "", title: str = ""):
        db = AppDatabase()
        db.set_setting(_SETTING_TIMER_START, start_iso)
        db.set_setting(_SETTING_TIMER_TAG, tag)
        db.set_setting(_SETTING_TIMER_TITLE, title)

    @staticmethod
    def get_timer_state() -> dict:
        db = AppDatabase()
        start = db.get_setting(_SETTING_TIMER_START) or ""
        return {
            "running": bool(start),
            "start_time": start or None,
            "tag": db.get_setting(_SETTING_TIMER_TAG) or None,
            "title": db.get_setting(_SETTING_TIMER_TITLE) or None,
        }

    @staticmethod
    def clear_timer_state():
        db = AppDatabase()
        for key in (_SETTING_TIMER_START, _SETTING_TIMER_TAG, _SETTING_TIMER_TITLE):
            db.delete_setting(key)


class ManualEntriesDataSource(SQLModelDataSourceMixin):
    """Manual time entries are ``TimeTrackingItem`` rows that belong to no timesheet."""

    def load_frame(self) -> Optional[DataFrame]:
        with self.create_session() as session:
            items = session.exec(sqlmodel.select(TimeTrackingItem).where(TimeTrackingItem.timesheet_id.is_(None))).all()
        if not items:
            return None
        rows = [
            {
                "title": item.title,
                "tag": item.tag,
                "description": item.description or "",
                "duration": item.duration,
                "all_day": False,
                "end": to_cet(item.end),
                "source": "manual",
                "entry_id": item.id,
            }
            for item in items
        ]
        index = pandas.DatetimeIndex([to_cet(item.begin) for item in items], name="begin")
        return DataFrame(rows, index=index)

    def add(self, begin, end, tag: str, title: str) -> int:
        begin, end = _naive_cet(begin), _naive_cet(end)
        item = TimeTrackingItem(
            begin=begin,
            end=end,
            duration=end - begin,
            title=title,
            tag=tag,
            description="",
        )
        self.store(item)
        return item.id

    def update(self, entry_id: int, begin, end, tag: str, title: str) -> bool:
        with self.create_session() as session:
            item = session.get(TimeTrackingItem, entry_id)
            if item is None or item.timesheet_id is not None:
                return False
            item.begin, item.end = _naive_cet(begin), _naive_cet(end)
            item.duration = item.end - item.begin
            item.tag, item.title = tag, title
            session.add(item)
            session.commit()
        return True

    def delete(self, entry_id: int) -> bool:
        with self.create_session() as session:
            item = session.get(TimeTrackingItem, entry_id)
            if item is None or item.timesheet_id is not None:
                return False
            session.delete(item)
            session.commit()
        return True


class TimeTrackingSpreadsheetSource:
    """Processes spreadsheets"""

    def __init__(self):
        super().__init__()

    def load_data(
        self,
        file_path: str,
    ) -> DataFrame:
        """loads time tracking data from a spreadsheet file

        Arguments:
            file_path : path to an uploaded spreadsheet file

        Returns:
            DataFrame: time tracking data
        """
        logger.info(f"Loading time tracking data from {file_path}...")
        timetracking_data: DataFrame = timetracking.import_from_spreadsheet(
            path=file_path,
            preset=timetracking.TogglPreset,
        )
        return timetracking_data


class TimeTrackingFileCalendarSource:
    """Processes calendars from a file"""

    def __init__(self) -> None:
        super().__init__()

    def load_data(
        self,
        ics_file_path,
    ) -> DataFrame:
        """loads time tracking data from a .ics file

        Args:
            ics_file_path : path to an uploaded ics or spreadsheet file

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : Calendar if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        file_calendar: ICSCalendar = ICSCalendar(
            name=ics_file_path.name,
            path=ics_file_path,
        )
        calendar_data: DataFrame = file_calendar.to_data()
        return calendar_data
