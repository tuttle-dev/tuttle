from core.abstractions import SQLModelDataSourceMixin

from core.intent_result import IntentResult
from .model import CloudCalendarInfo


class TimeTrackingDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the TimeTracking data in the database"""

    def __init__(self):
        super().__init__()

    def load_from_timetracking_file(self, file_path) -> IntentResult:
        """TODO load the time tracking data

        Arguments:
            file_path : path to an uploaded ics or spreadsheet file

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  #TODO? was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            return IntentResult(
                was_intent_successful=False, log_message="Un Implemented error"
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @TimeTrackingDataSource.load_from_timetracking_file {e.__class__.__name__}",
                exception=e,
            )

    def configure_account_and_load_calendar(
        self,
        info: CloudCalendarInfo,
    ) -> IntentResult:
        """TODO Attempts to login and log data given CloudCalendarInfo

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  #TODO? was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        # TODO: use tuttle.cloud.login_iCloud() to log in to iCloud
        try:
            return IntentResult(
                was_intent_successful=False, log_message="Un Implemented error"
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @TimeTrackingDataSource.configure_account_and_load_calendar {e.__class__.__name__}",
                exception=e,
            )
