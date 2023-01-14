from .data_source import TimeTrackingDataSource
from core.abstractions import ClientStorage
from core.intent_result import IntentResult
from preferences.model import PreferencesStorageKeys, CloudAccounts
from preferences.intent import PreferencesIntent
from .model import CloudCalendarInfo, CloudConfigurationResult
from typing import Optional


class TimeTrackingIntent:
    """Handles TimeTrackingIntent C_R_U_D intents

    Intents handled (Methods)
    ---------------
    configure_account_and_load_calendar_intent
        configuring and loading a calendar from CloudCalendarInfo
    get_preferred_cloud_account_intent
        fetching the [cloud_provider, cloud_account_name] from preferences
    process_timetracking_file_intent
        processing info given an ics or spreadsheet file
    """

    def __init__(self, local_storage: ClientStorage):
        """
        Attributes
        ----------
        _data_source : TimeTrackingDataSource
            reference to the TimeTracking data source
        _preferences_intent : PreferencesIntent
            reference to the PreferencesIntent for forwarding preferences related intents
        """
        self._data_source = TimeTrackingDataSource()
        self._preferences_intent = PreferencesIntent(local_storage)

    def process_timetracking_file_intent(self, upload_url, file_name) -> IntentResult:
        """TODO processes a time tracking spreadsheet or ics file in the uploads folder"""
        result = IntentResult(
            was_intent_successful=False,
            error_msg="Processing file failed",
            log_message=f"Un Implemented error TimeTrackingIntent.process_timetracking_file",
        )
        result.log_message_if_any()
        return result

    def get_preferred_cloud_account_intent(self):
        """
        Returns:
            IntentResult
                data as [provider_name, account_name] list if successful else None"""
        provider_result = self._preferences_intent.get_preference_by_key_intent(
            PreferencesStorageKeys.cloud_provider_key
        )
        acc_result = self._preferences_intent.get_preference_by_key_intent(
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

    def _set_preferred_cloud_account_intent(self, cloud_acc_id, cloud_provider):
        result = self._preferences_intent.set_preference_key_value_pair_intent(
            PreferencesStorageKeys.cloud_provider_key, cloud_provider
        )
        if not result.was_intent_successful:
            return result  # do not proceed
        return self._preferences_intent.set_preference_key_value_pair_intent(
            PreferencesStorageKeys.cloud_acc_id_key, cloud_acc_id
        )

    def configure_account_and_load_calendar_intent(
        self,
        calendar_info: CloudCalendarInfo,
        two_factor_code: Optional[str] = "",
        prev_un_verified_login_res: Optional[CloudConfigurationResult] = None,
    ):
        """Attempts to configure cloud account and load data given CloudCalendarInfo
        *This is a multi-step process

        Params
        ------
        calendar_info: CloudCalendarInfo
            information about the calendar to load and it's associated account
        two_factor_code: Optional[str]
            set during an Optional second step if user has been asked to enter a 2fa code
        prev_un_verified_login_res : CloudConfigurationResult
            keeps track of the session if any that is pending a 2fa code

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
                res = self._data_source.login_to_icloud(calendar_info=calendar_info)
            else:
                # TODO other providers - we assume only google below?
                res = self._data_source.login_to_google(calendar_info=calendar_info)
        else:
            # STEP 2 complete login with 2FA
            if calendar_info.provider == CloudAccounts.ICloud.value:
                res = self._data_source.verify_icloud_with_2fa(
                    login_result=prev_un_verified_login_res,
                    two_factor_code=two_factor_code,
                )
            else:
                # TODO other providers - we assume only google below?
                res = self._data_source.verify_google_with_2fa(
                    login_result=prev_un_verified_login_res,
                    two_factor_code=two_factor_code,
                )
        config_result: CloudConfigurationResult = res.data
        if config_result and config_result.cloud_acc_configured_successfully:
            # proceed to load cloud calendar data
            res = self._data_source.load_cloud_calendar_data(
                info=calendar_info, cloud_session=res.session_ref
            )
        if not res.was_intent_successful:
            res.error_msg = "Loading calendar data failed! Please retry"
            res.log_message_if_any()
        return res
