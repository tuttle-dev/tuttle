from .data_source import TimeTrackingDataSource
from core.abstractions import ClientStorage
from core.models import IntentResult
from preferences.model import PreferencesStorageKeys
from preferences.intent import PreferencesIntent
from .model import CloudCalendarInfo


class TimeTrackingIntent:
    """Handles events from the time tracking views"""

    def __init__(self, local_storage: ClientStorage):
        self.data_source = TimeTrackingDataSource()
        self.preferences_intent = PreferencesIntent(local_storage)

    def process_timetracking_file(self, upload_url, file_name):
        """processes a time tracking spreadsheet or ics file in the uploads folder"""
        result = self.data_source.process_timetracking_file(file_name)
        if not result.was_intent_successful:
            result.error_msg = f"Failed to process the file {file_name}"
        return result

    def get_preferred_cloud_account(self):
        """ïf successful returns data as a list [provider_name, account_name]"""
        provider_result = self.preferences_intent.get_preference(
            PreferencesStorageKeys.cloud_provider_key
        )
        acc_result = self.preferences_intent.get_preference(
            PreferencesStorageKeys.cloud_acc_id_key
        )
        if (
            not provider_result.was_intent_successful
            or not acc_result.was_intent_successful
        ):
            return IntentResult(
                was_intent_successful=False,
                error_msg_if_err="Failed to load account preferences",
            )
        print(f"{provider_result.data},  {acc_result.data}")
        return IntentResult(
            was_intent_successful=True, data=[provider_result.data, acc_result.data]
        )

    def set_preferred_cloud_account(self, cloud_acc_id, cloud_provider):
        result = self.preferences_intent.set_preference(
            PreferencesStorageKeys.cloud_provider_key, cloud_provider
        )
        if not result.was_intent_successful:
            return result  # do not proceed
        return self.preferences_intent.set_preference(
            PreferencesStorageKeys.cloud_acc_id_key, cloud_acc_id
        )

    def configure_account_and_load_calendar(
        self, info: CloudCalendarInfo, save_as_preferred
    ) -> IntentResult:
        result = self.data_source.configure_account_and_load_calendar(info)
        if result.was_intent_successful and save_as_preferred:
            self.set_preferred_cloud_account(info.account, info.provider)
        return result
