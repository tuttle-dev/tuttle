from .data_source import TimeTrackingDataSource
from core.abstractions import ClientStorage
from core.models import IntentResult


class TimeTrackingIntent:
    """Handles events from the time tracking views"""

    def __init__(self, local_storage: ClientStorage):
        self.data_source = TimeTrackingDataSource()
        self.local_storage = local_storage

    def process_timetracking_file(self, file_name):
        """processes a time tracking spreadsheet or ics file in the uploads folder"""
        result = self.data_source.process_timetracking_file(file_name)
        if not result.was_intent_successful:
            result.error_msg = f"Failed to process the file {file_name}"
        return result
