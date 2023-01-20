from typing import Type, Union, Any

import icloudpy

from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult
from pandas import DataFrame

from tuttle.calendar import ICSCalendar, ICloudCalendar, CloudCalendar
from tuttle.dev import singleton
from tuttle.cloud import CloudConnector


@singleton
class TimeTrackingDataFrameSource:
    """Provides get or edit access to the data frame in memory"""

    def __init__(self):
        super().__init__()
        self.data: DataFrame = None

    def get_data_frame(self) -> DataFrame:
        return self.data

    def store_data_frame(self, data: DataFrame):
        self.data = data


class TimeTrackingFileCalendarSource:
    """Processes calendars from a file"""

    def __init__(self) -> None:
        super().__init__()

    def load_timetracking_data_from_spreadsheet(
        self,
        spreadsheet_file_name: str,
        spreadsheet_file_path: str,
    ):
        """TODO loads time tracking data from a spreadsheet file

        Arguments:
            file_name : name of the uploaded file
            file_path : path to an uploaded ics or spreadsheet file

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : Calendar if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        return IntentResult(
            was_intent_successful=False,
            log_message="Un impemented error @TimeTrackingDataSource.load_timetracking_data_from_spreadsheet",
        )

    def load_timetracking_data_from_ics_file(
        self,
        ics_file_name: str,
        ics_file_path,
    ) -> IntentResult:
        """loads time tracking data from a .ics file

        Arguments:
            ics_file_name : name of the uploaded file
            ics_file_path : path to an uploaded ics or spreadsheet file

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : Calendar if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            file_calendar: ICSCalendar = ICSCalendar(
                name=ics_file_name, path=ics_file_path
            )
            return IntentResult(was_intent_successful=True, data=file_calendar)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @TimeTrackingDataSource.load_from_timetracking_file {e.__class__.__name__}",
                exception=e,
            )


class TimeTrackingCloudCalendarSource:
    """Configures and processes calendar data from the cloud"""

    def __init__(self):
        super().__init__()

    def load_cloud_calendar_data(
        self,
        calendar_name: str,
        cloud_connector: CloudConnector,
    ) -> DataFrame:
        """Loads data from a cloud calendar"""
        calendar = None
        if cloud_connector.provider == "iCloud":
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
        )

    """ GOOGLE LOGIN STEPS """

    def login_to_google(
        self,
        google_account: str,
        google_account_password: str,
    ):
        """TODO Attempts to authenticate user with their google account"""
        raise NotImplementedError
