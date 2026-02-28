from typing import Optional

from pathlib import Path

from loguru import logger
from pandas import DataFrame

from ..core.abstractions import ClientStorage, Intent
from ..core.intent_result import IntentResult

from .data_source import (
    SYSTEM_CALENDAR_AVAILABLE,
    TimeTrackingDataFrameSource,
    TimeTrackingFileCalendarSource,
    TimeTrackingSystemCalendarSource,
    TimeTrackingSpreadsheetSource,
)


class TimeTrackingIntent(Intent):
    """Handles time tracking intents"""

    def __init__(self, client_storage: ClientStorage):
        self._file_calendar_source = TimeTrackingFileCalendarSource()
        self._spreadsheet_source = TimeTrackingSpreadsheetSource()
        self._timetracking_data_frame_source = TimeTrackingDataFrameSource()
        if SYSTEM_CALENDAR_AVAILABLE:
            self._system_calendar_source = TimeTrackingSystemCalendarSource()
        else:
            self._system_calendar_source = None

    def process_timetracking_file(self, file_path: Path) -> IntentResult[DataFrame]:
        """Processes a time tracking spreadsheet or ics file."""
        is_calendar = file_path.suffix == ".ics"
        if is_calendar:
            timetracking_data: DataFrame = self._file_calendar_source.load_data(
                ics_file_path=file_path,
            )
        else:
            timetracking_data: DataFrame = self._spreadsheet_source.load_data(
                file_path=file_path,
            )
        return IntentResult(
            was_intent_successful=True,
            data=timetracking_data,
        )

    def list_system_calendars(self) -> IntentResult[list[dict]]:
        """Returns available system calendars."""
        if self._system_calendar_source is None:
            return IntentResult(
                was_intent_successful=False,
                error_msg="System calendar is not available on this platform",
            )
        try:
            calendars = self._system_calendar_source.list_calendars()
            return IntentResult(
                was_intent_successful=True,
                data=calendars,
            )
        except Exception as ex:
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to list system calendars",
                exception=ex,
            )

    def load_from_system_calendar(self, calendar_name: str) -> IntentResult[DataFrame]:
        """Loads time tracking data from a system calendar."""
        if self._system_calendar_source is None:
            return IntentResult(
                was_intent_successful=False,
                error_msg="System calendar is not available on this platform",
            )
        try:
            calendar_data = self._system_calendar_source.load_data(
                calendar_name=calendar_name,
            )
            return IntentResult(
                was_intent_successful=True,
                data=calendar_data,
            )
        except Exception as ex:
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load data from calendar '{calendar_name}'",
                exception=ex,
            )

    def get_timetracking_data(self) -> IntentResult[Optional[DataFrame]]:
        try:
            data = self._timetracking_data_frame_source.get_data_frame()
            return IntentResult(
                was_intent_successful=True,
                data=data,
            )
        except Exception as ex:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to load time tracking data",
                exception=ex,
                data=None,
            )

    def set_timetracking_data(self, data: DataFrame) -> IntentResult[None]:
        try:
            self._timetracking_data_frame_source.store_data_frame(data=data)
            return IntentResult(
                was_intent_successful=True,
            )
        except Exception as ex:
            error_msg = "Failed to store time tracking data"
            logger.error(error_msg)
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_msg,
                exception=ex,
                data=None,
            )
