import datetime
import shutil
from pathlib import Path
from typing import Optional

import pandas
import sqlmodel
from loguru import logger
from pandas import DataFrame

from ... import timetracking
from ...calendar import ICSCalendar
from ...dev import singleton
from ...model import TimeTrackingItem, TimeTrackingSettings
from ..core.abstractions import SQLModelDataSourceMixin, get_active_db
from ..core.rpc_utils import register_reset
from .aggregation import merge_dataframes

TZ = "CET"


def to_cet(dt) -> pandas.Timestamp:
    # Calendar sources index events in CET; a row in another zone (or naive)
    # makes pandas degrade the whole index to dtype object, breaking `.date`.
    ts = pandas.Timestamp(dt)
    return ts.tz_convert(TZ) if ts.tzinfo else ts.tz_localize(TZ)


def _naive_cet(dt):
    # SQLite drops tzinfo, so rows are stored as CET wall-clock time.
    return to_cet(dt).tz_localize(None).to_pydatetime()


def user_cache_dir(db_path: Path) -> Path:
    """Cache directory of the user whose database is *db_path*.

    Calendar events are private to one user, so each user gets their own
    directory next to their database; nothing is shared between users.
    """
    db_path = Path(db_path)
    return db_path.parent / "cache" / db_path.stem


def calendar_cache_path(db_path: Optional[Path] = None) -> Path:
    return user_cache_dir(db_path or get_active_db()) / "timetracking_events.parquet"


def write_calendar_cache(db_path: Path, calendar: DataFrame):
    """Persist calendar rows for the user whose database is *db_path*."""
    path = calendar_cache_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    calendar.to_parquet(path)
    logger.info(f"Persisted {len(calendar)} calendar events to {path}")


def delete_user_cache(db_path: Path):
    shutil.rmtree(user_cache_dir(db_path), ignore_errors=True)


class TimeTrackingSettingsSource:
    """Calendar connection and running timer, stored in one user's database.

    Defaults to the active user; pass *db_path* to address another user's
    database explicitly (e.g. installing the demo user while someone else is active).
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_url = f"sqlite:///{db_path or get_active_db()}"

    def _run(self, fn):
        engine = sqlmodel.create_engine(self._db_url)
        try:
            with sqlmodel.Session(engine, expire_on_commit=False) as session:
                return fn(session)
        finally:
            engine.dispose()

    def get(self) -> TimeTrackingSettings:
        row = self._run(lambda session: session.exec(sqlmodel.select(TimeTrackingSettings)).first())
        return row or TimeTrackingSettings()

    def update(self, **fields):
        def _update(session):
            row = session.exec(sqlmodel.select(TimeTrackingSettings)).first() or TimeTrackingSettings()
            for key, value in fields.items():
                setattr(row, key, value)
            session.add(row)
            session.commit()

        self._run(_update)


def _to_naive_utc(iso: str) -> datetime.datetime:
    ts = datetime.datetime.fromisoformat(iso)
    if ts.tzinfo is not None:
        ts = ts.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return ts


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
    # Everything below reads and writes the *active* user's database and cache
    # directory. Nothing here may live in app.db or a shared file.

    def save_to_cache(self):
        calendar = self.calendar_rows()
        if calendar is None:
            return
        try:
            write_calendar_cache(get_active_db(), calendar)
        except Exception as ex:
            logger.warning(f"Failed to persist time-tracking cache: {ex}")

    def load_from_cache(self) -> bool:
        path = calendar_cache_path()
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
        path = calendar_cache_path()
        if path.exists():
            path.unlink()

    @staticmethod
    def save_source_config(source_type: str, calendar_id: str = "", calendar_name: str = ""):
        TimeTrackingSettingsSource().update(
            calendar_source=source_type,
            calendar_id=calendar_id or None,
            calendar_name=calendar_name or None,
        )

    @staticmethod
    def get_source_config() -> dict:
        row = TimeTrackingSettingsSource().get()
        return {
            "source_type": row.calendar_source or "",
            "calendar_id": row.calendar_id or "",
            "calendar_name": row.calendar_name or "",
        }

    @staticmethod
    def clear_source_config():
        TimeTrackingSettingsSource().update(calendar_source=None, calendar_id=None, calendar_name=None)

    # -- timer state -----------------------------------------------------------

    @staticmethod
    def save_timer_state(start_iso: str, tag: str = "", title: str = ""):
        TimeTrackingSettingsSource().update(
            timer_start=_to_naive_utc(start_iso),
            timer_tag=tag or None,
            timer_title=title or None,
        )

    @staticmethod
    def get_timer_state() -> dict:
        row = TimeTrackingSettingsSource().get()
        start = row.timer_start.replace(tzinfo=datetime.timezone.utc).isoformat() if row.timer_start else None
        return {
            "running": start is not None,
            "start_time": start,
            "tag": row.timer_tag or None,
            "title": row.timer_title or None,
        }

    @staticmethod
    def clear_timer_state():
        TimeTrackingSettingsSource().update(timer_start=None, timer_tag=None, timer_title=None)


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
