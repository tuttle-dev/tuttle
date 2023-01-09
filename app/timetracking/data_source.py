from core.abstractions import ClientStorage, SQLModelDataSourceMixin

from core.models import IntentResult

from tuttle.model import Address, User


class TimeTrackingDataSource(SQLModelDataSourceMixin):
    def __init__(self):
        super().__init__()

    def process_timetracking_file(self, file_name):
        """process a recently uploaded time tracking file in .xlsx or .ics format
        returns was_intent_successful = True if processing completed successfully
        else was_intent_successful = False and err_msg are set
        """
        return IntentResult(was_intent_successful=True, data=None)
