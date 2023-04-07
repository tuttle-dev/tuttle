from typing import Optional, Type, Union

from pathlib import Path

from loguru import logger


from core.abstractions import ClientStorage, Intent
from core.intent_result import IntentResult
from pandas import DataFrame
from preferences.intent import PreferencesIntent
from preferences.model import PreferencesStorageKeys

from .data_source import (
    TimeTrackingCloudCalendarSource,
    TimeTrackingDataFrameSource,
    TimeTrackingFileCalendarSource,
    TimeTrackingSpreadsheetSource,
)
from tuttle.cloud import CloudConnector, CloudProvider
from tuttle.calendar import Calendar


class TimeTrackingIntent(Intent):
    """Handles time tracking intents"""

    def __init__(self, client_storage: ClientStorage):

        self._cloud_calendar_source = TimeTrackingCloudCalendarSource()
        self._file_calendar_source = TimeTrackingFileCalendarSource()
        self._spreadsheet_source = TimeTrackingSpreadsheetSource()
        self._timetracking_data_frame_source = TimeTrackingDataFrameSource()
        self._preferences_intent = PreferencesIntent(client_storage)

    def get_preferred_cloud_account(self) -> IntentResult[Optional[list]]:
        """
        Returns:
            IntentResult
                data as [provider_name, account_name] list if successful else None"""
        provider_result = self._preferences_intent.get_preference_by_key(
            PreferencesStorageKeys.cloud_provider_key
        )
        acc_result = self._preferences_intent.get_preference_by_key(
            PreferencesStorageKeys.cloud_acc_id_key
        )
        if (
            not provider_result.was_intent_successful
            or not acc_result.was_intent_successful
        ):
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to load account preferences",
            )
        return IntentResult(
            was_intent_successful=True, data=[provider_result.data, acc_result.data]
        )

    def process_timetracking_file(self, file_path: Path) -> IntentResult[DataFrame]:
        """processes a time tracking spreadsheet or ics file in the uploads folder

        Returns
        -------
            IntentResult
                data : time tracking data as a pandas DataFrame if intent successful else None
                error_msg  : text to display to the user if an error occurs else is empty
        """
        # check the file extension. file_path is a Path object
        is_calendar = file_path.suffix == ".ics"
        if is_calendar:
            timetracking_data: DataFrame = self._file_calendar_source.load_data(
                ics_file_path=file_path,
            )
            return IntentResult(
                was_intent_successful=True,
                data=timetracking_data,
            )
        else:
            timetracking_data: DataFrame = self._spreadsheet_source.load_data(
                file_path=file_path,
            )
            return IntentResult(
                was_intent_successful=True,
                data=timetracking_data,
            )

    def connect_to_cloud(
        self,
        provider: str,
        account_id: str,
        password: str,
    ) -> IntentResult[CloudConnector]:
        """"""
        try:
            # check cloud_calendar_info for the value of the cloud provider
            # if it is icloud, call the login_to_icloud method
            logger.info(
                f"Trying to connect to cloud provider {provider} with account {account_id}"
            )
            if provider == CloudProvider.ICloud.value:
                connector: CloudConnector = self._cloud_calendar_source.login_to_icloud(
                    apple_id=account_id,
                    password=password,
                )
                logger.info(
                    f"Successfully connected to iCloud with account {account_id}"
                )
                return IntentResult(
                    was_intent_successful=True,
                    data=connector,
                )
            else:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg=f"Not implemented yet for cloud provider {provider}",
                )
        except Exception as ex:
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to connect to cloud provider {provider}",
                exception=ex,
            )

    def load_from_cloud_calendar(
        self,
        cloud_connector: CloudConnector,
        calendar_name: str,
    ) -> IntentResult[DataFrame]:
        """Loads time tracking data from a cloud calendar using a cloud connector"""
        try:
            calendar_data: DataFrame = self._cloud_calendar_source.load_data(
                cloud_connector=cloud_connector,
                calendar_name=calendar_name,
            )
            return IntentResult(
                was_intent_successful=True,
                data=calendar_data,
            )
        except Exception as ex:
            error_message = f"Failed to load data from cloud calendar {calendar_name}"
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_message,
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

    # def get_time_spent_for_project(self, project: Project) -> IntentResult[float]:
    #     raise NotImplementedError("TODO")
