from .data_source import (
    TimeTrackingCloudCalendarSource,
    TimeTrackingDataFrameSource,
    TimeTrackingFileCalendarSource,
)
from typing import Type, Union
from pandas import DataFrame
from core.abstractions import ClientStorage
from core.intent_result import IntentResult
from preferences.model import PreferencesStorageKeys, CloudAccounts
from preferences.intent import PreferencesIntent
from .model import CloudCalendarInfo, CloudConfigurationResult
from typing import Optional


class TimeTrackingIntent:
    """Handles TimeTrackingIntent C_R_U_D intents"""

    def __init__(self, local_storage: ClientStorage):

        self._timetracking_cloud_data_source = TimeTrackingCloudCalendarSource()
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

    def _set_preferred_cloud_account(self, cloud_acc_id, cloud_provider):
        result = self._preferences_intent.set_preference_key_value_pair(
            PreferencesStorageKeys.cloud_provider_key, cloud_provider
        )
        if not result.was_intent_successful:
            return result  # do not proceed
        return self._preferences_intent.set_preference_key_value_pair(
            PreferencesStorageKeys.cloud_acc_id_key, cloud_acc_id
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

    def configure_account_and_load_calendar(
        self,
        calendar_info: CloudCalendarInfo,
        two_factor_code: Optional[str] = "",
        prev_un_verified_login_res: Optional[CloudConfigurationResult] = None,
    ) -> IntentResult[Union[Type[CloudConfigurationResult], None]]:
        """Configures cloud account and loads calendar data

        *Multi-step process

        Parameters:
        calendar_info (CloudCalendarInfo) : Calendar information
        two_factor_code (Optional[str]) : Two factor code for login
        prev_un_verified_login_res (Optional[CloudConfigurationResult]) : Previous login result

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : CloudConfigurationResult if was_intent_successful else None
                    the data result can be CloudConfigurationResult(request_2fa_code = True) if a 2fa code is needed
                    Or CloudConfigurationResult(request_2fa_code = True, provided_2fa_code_is_invalid = True) if a 2fa code is needed and the user just provided an incorrect one
                    Or CloudConfigurationResult(cloud_acc_configured_successfully = True) when and if configuration steps complete successfully and a cloud session is created (user is logged in)
                    Or CloudConfigurationResult(calendar_loaded_successfully = True) if calendar data is loaded succesffuly
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """

        res: IntentResult = None
        if not two_factor_code:
            # STEP 1 user is login in
            if calendar_info.provider == CloudAccounts.ICloud.value:
                res = self._timetracking_cloud_data_source.login_to_icloud(
                    calendar_info=calendar_info
                )
            else:

                res = self._timetracking_cloud_data_source.login_to_google(
                    calendar_info=calendar_info
                )
        else:
            # STEP 2 complete login with 2FA
            if calendar_info.provider == CloudAccounts.ICloud.value:
                res = self._timetracking_cloud_data_source.verify_icloud_with_2fa(
                    login_result=prev_un_verified_login_res,
                    two_factor_code=two_factor_code,
                )
            else:

                res = self._timetracking_cloud_data_source.verify_google_with_2fa(
                    login_result=prev_un_verified_login_res,
                    two_factor_code=two_factor_code,
                )
        config_result: CloudConfigurationResult = res.data
        if config_result and config_result.cloud_acc_configured_successfully:
            # proceed to load cloud calendar data
            res = self._timetracking_cloud_data_source.load_cloud_calendar_data(
                info=calendar_info, cloud_session=config_result.session_ref
            )
        if not res.was_intent_successful:
            res.error_msg = "Loading calendar data failed! Please retry"
            res.log_message_if_any()
        return res

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
        self._timetracking_data_frame_source.store_data_frame(data=data)
