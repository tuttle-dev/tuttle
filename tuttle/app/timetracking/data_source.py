from typing import Optional

from loguru import logger
from pandas import DataFrame

from ...calendar import ICSCalendar, system_calendar_available
from ...dev import singleton
from ... import timetracking

SYSTEM_CALENDAR_AVAILABLE = system_calendar_available()


@singleton
class TimeTrackingDataFrameSource:
    """Provides get or edit access to the data frame in memory"""

    def __init__(self):
        super().__init__()
        self.data: Optional[DataFrame] = None

    def get_data_frame(self) -> DataFrame:
        return self.data

    def store_data_frame(self, data: DataFrame):
        self.data = data


class TimeTrackingSpreadsheetSource:
    """Processes spreadsheets"""

    def __init__(self):
        super().__init__()

    def load_data(
        self,
        file_path: str,
    ) -> DataFrame:
        """Loads time tracking data from a spreadsheet file."""
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
        """Loads time tracking data from a .ics file."""
        file_calendar: ICSCalendar = ICSCalendar(
            name=ics_file_path.name,
            path=ics_file_path,
        )
        calendar_data: DataFrame = file_calendar.to_data()
        return calendar_data


class TimeTrackingSystemCalendarSource:
    """Loads time tracking data from the system calendar."""

    def list_calendars(self) -> list[dict]:
        """Returns all calendars available on this system."""
        if not SYSTEM_CALENDAR_AVAILABLE:
            return []
        from ...calendar import SystemCalendar

        cal = SystemCalendar()
        return cal.list_available_calendars()

    def load_data(self, calendar_name: str) -> DataFrame:
        """Loads events from a named system calendar as time tracking data."""
        from ...calendar import SystemCalendar

        cal = SystemCalendar(name=calendar_name)
        return cal.to_data()
