from core.abstractions import SQLModelDataSourceMixin, IntentResult

from tuttle.model import (
    Invoice,
)


class InvoicingDataSource(SQLModelDataSourceMixin):
    def __init__(self):
        super().__init__()

    def get_invoices_for_project(self, project_id) -> IntentResult:
        """TODO returns data as existing invoices associated with the project or None if none exists"""
        return IntentResult(was_intent_successful=True, data=None)

    def get_all_invoices(self) -> IntentResult:
        """Gets all invoices from the database"""
        try:
            invoices = self.query(Invoice)
            return IntentResult(
                was_intent_successful=True,
                data=invoices,
            )
        except Exception as ex:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Error getting all invoices: {ex.__class__.__name__}",
                exception=ex,
            )
