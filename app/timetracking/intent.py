from .data_source import TimeTrackingDataSource
from core.abstractions import ClientStorage
from core.models import IntentResult
from preferences.model import PreferencesStorageKeys
from preferences.intent import PreferencesIntent
from .model import ICloudCalendarInfo


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

    def get_preferred_icloud_account(self):
        return self.preferences_intent.get_preference(
            PreferencesStorageKeys.icloud_acc_id_key
        )

    def set_preferred_icloud_account(self, icloud_acc):
        return self.preferences_intent.set_preference(
            PreferencesStorageKeys.icloud_acc_id_key, icloud_acc
        )

    def configure_icloud_and_load_calendar(
        self, info: ICloudCalendarInfo, save_as_preferred
    ) -> IntentResult:
        result = self.data_source.configure_icloud_and_load_calendar(info)
        if result.was_intent_successful and save_as_preferred:
            self.set_preferred_icloud_account(info.account)
        return result
