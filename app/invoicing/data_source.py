from core.abstractions import SQLModelDataSourceMixin, IntentResult


class InvoicingDataSource(SQLModelDataSourceMixin):
    def __init__(self):
        super().__init__()

    def get_invoices_for_project(self, project_id) -> IntentResult:
        """TODO returns data as existing invoices associated with the project or None if none exists"""
        return IntentResult(was_intent_successful=True, data=None)
