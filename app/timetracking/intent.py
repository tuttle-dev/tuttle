from .data_source import TimeTrackingDataSource
from core.abstractions import ClientStorage
from core.models import IntentResult
from preferences.intent import PreferencesIntent
from .model import ICloudCalendarInfo


class TimeTrackingIntent:
    """Handles events from the time tracking views"""

    def __init__(self, local_storage: ClientStorage):
        self.data_source = TimeTrackingDataSource()
        self.preferences_intent = PreferencesIntent(local_storage)

    def process_timetracking_file(self, file_name):
        """processes a time tracking spreadsheet or ics file in the uploads folder"""
        result = self.data_source.process_timetracking_file(file_name)
        if not result.was_intent_successful:
            result.error_msg = f"Failed to process the file {file_name}"
        return result

    def get_preferred_icloud_account(self):
        return self.preferences_intent.get_icloud_account()

    def set_preferred_icloud_account(self, icloud_acc):
        return self.preferences_intent.set_preferred_icloud_account(
            icloud_acc_id=icloud_acc
        )

    def configure_icloud_and_load_calendar(
        self, info: ICloudCalendarInfo
    ) -> IntentResult:
        return self.data_source.configure_icloud_and_load_calendar(info)
