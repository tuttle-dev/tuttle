from typing import Type, Union, Any, Optional

from loguru import logger
import icloudpy

from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult
from pandas import DataFrame

from tuttle.calendar import ICSCalendar, ICloudCalendar, CloudCalendar
from tuttle.dev import singleton
from tuttle.cloud import CloudConnector, CloudProvider
from tuttle import timetracking


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


class TimeTrackingCloudCalendarSource:
    """Configures and processes calendar data from the cloud"""

    def __init__(self):
        super().__init__()

    def load_data(
        self,
        calendar_name: str,
        cloud_connector: CloudConnector,
    ) -> DataFrame:
        """Loads data from a cloud calendar"""
        calendar = None
        if cloud_connector.provider == CloudProvider.ICloud.value:
            icloud_connector: icloudpy.ICloudPyService = (
                cloud_connector.concrete_connector
            )
            calendar: CloudCalendar = ICloudCalendar(
                name=calendar_name,
                icloud_connector=icloud_connector,
            )
        else:
            raise NotImplementedError

        calendar_data: DataFrame = calendar.to_data()
        return calendar_data

    def login_to_icloud(
        self,
        apple_id: str,
        password: str,
    ) -> CloudConnector:
        """Attempts to authenticate user with their icloud account"""
        # TODO: error handling - login may fail
        icloud_connector = icloudpy.ICloudPyService(
            apple_id=apple_id,
            password=password,
        )
        return CloudConnector(
            cloud_connector=icloud_connector,
            account_name=apple_id,
        )

    """ GOOGLE LOGIN STEPS """

    def login_to_google(
        self,
        google_account: str,
        google_account_password: str,
    ):
        """TODO Attempts to authenticate user with their google account"""
        raise NotImplementedError
