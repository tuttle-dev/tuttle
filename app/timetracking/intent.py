from typing import Optional, Type, Union

from loguru import logger

from core.abstractions import ClientStorage
from core.intent_result import IntentResult
from pandas import DataFrame
from preferences.intent import PreferencesIntent
from preferences.model import PreferencesStorageKeys

from .data_source import (
    TimeTrackingCloudCalendarSource,
    TimeTrackingDataFrameSource,
    TimeTrackingFileCalendarSource,
)
from tuttle.cloud import CloudConnector, CloudProvider


class TimeTrackingIntent:
    """Handles time tracking intents"""

    def __init__(self, local_storage: ClientStorage):

        self._cloud_calendar_source = TimeTrackingCloudCalendarSource()
        self._timetracking_file_data_source = TimeTrackingFileCalendarSource()
        self._timetracking_data_frame_source = TimeTrackingDataFrameSource()
        self._preferences_intent = PreferencesIntent(local_storage)

    def get_preferred_cloud_account(self):
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

    def process_timetracking_file(self, file_path, file_name) -> IntentResult:
        """processes a time tracking spreadsheet or ics file in the uploads folder

        Returns
        -------
            IntentResult
                data : Calendar instance if was_intent_successful else None
                error_msg  : text to display to the user if an error occurs else is empty
        """
        is_ics = ".ics" in file_name
        if is_ics:
            result = self._timetracking_file_data_source.load_timetracking_data_from_ics_file(
                ics_file_name=file_name,
                ics_file_path=file_path,
            )
        else:
            result = self._timetracking_file_data_source.load_timetracking_data_from_spreadsheet(
                spreadsheet_file_name=file_name, spreadsheet_file_path=file_path
            )
        if not result.was_intent_successful:
            result.error_msg = (
                "Failed to process the file! Please make sure it has a valid format."
            )
            result.log_message_if_any()
        return result

    def connect_to_cloud(
        self,
        provider: CloudProvider,
        account_name: str,
        password: str,
    ) -> IntentResult[CloudConnector]:
        """"""
        # check cloud_calendar_info for the value of the cloud provider
        # if it is icloud, call the login_to_icloud method

        if provider == CloudProvider.ICloud:
            connector: CloudConnector = self._cloud_calendar_source.login_to_icloud()
            # is a 2fa code required?
            return IntentResult(
                was_intent_successful=True,
                data=connector,
            )
        else:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Not implemented yet for cloud provider {provider}",
            )

    def load_from_cloud_calendar(
        self,
        cloud_connector: CloudConnector,
        calendar_name: str,
    ) -> IntentResult[DataFrame]:
        """Loads time tracking data from a cloud calendar using a cloud connector"""
        calendar_data: DataFrame = self._cloud_calendar_source.load_data(
            cloud_connector=cloud_connector,
            calendar_name=calendar_name,
        )
        return IntentResult(
            was_intent_successful=True,
            data=calendar_data,
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
