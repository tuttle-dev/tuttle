from pathlib import Path
from typing import Optional

from loguru import logger
from pandas import DataFrame

from ... import timetracking
from ...app_db import AppDatabase
from ...calendar import ICSCalendar
from ...data_dir import get_data_dir
from ...dev import singleton
from ..core.rpc_utils import register_reset

_SETTING_SOURCE_TYPE = "timetracking.source_type"
_SETTING_CALENDAR_ID = "timetracking.calendar_id"
_SETTING_CALENDAR_NAME = "timetracking.calendar_name"


def _cache_dir() -> Path:
    d = get_data_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


@singleton
class TimeTrackingDataFrameSource:
    """Provides get or edit access to the data frame in memory.

    Because this is a @singleton, its data survives intent resets.
    We register a reset callback so that switching users clears stale data.
    """

    def __init__(self):
        super().__init__()
        self.data: Optional[DataFrame] = None
        register_reset(self.clear)

    def get_data_frame(self) -> DataFrame:
        return self.data

    def store_data_frame(self, data: DataFrame):
        self.data = data

    def clear(self):
        self.data = None

    # -- persistence helpers ---------------------------------------------------

    def save_to_cache(self):
        if self.data is None or self.data.empty:
            return
        path = _cache_dir() / "timetracking_events.parquet"
        try:
            self.data.to_parquet(path)
            logger.info(f"Persisted {len(self.data)} events to {path}")
        except Exception as ex:
            logger.warning(f"Failed to persist time-tracking cache: {ex}")

    def load_from_cache(self) -> bool:
        path = _cache_dir() / "timetracking_events.parquet"
        if not path.exists():
            return False
        try:
            from pandas import read_parquet

            self.data = read_parquet(path)
            logger.info(f"Restored {len(self.data)} events from cache")
            return True
        except Exception as ex:
            logger.warning(f"Failed to load time-tracking cache: {ex}")
            return False

    def clear_cache(self):
        path = _cache_dir() / "timetracking_events.parquet"
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
