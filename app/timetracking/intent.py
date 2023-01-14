from .data_source import TimeTrackingDataSource
from core.abstractions import ClientStorage
from core.intent_result import IntentResult
from preferences.model import PreferencesStorageKeys
from preferences.intent import PreferencesIntent
from .model import CloudCalendarInfo
from tuttle import calendar


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
        self, info: CloudCalendarInfo, save_as_preferred
    ) -> IntentResult:
        result = self._data_source.configure_account_and_load_calendar(info)
        if result.was_intent_successful and save_as_preferred:
            # saves this account if to preferences
            self._set_preferred_cloud_account_intent(info.account, info.provider)
        else:
            result.log_message_if_any()
        return result
