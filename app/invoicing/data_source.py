from core.abstractions import SQLModelDataSourceMixin, IntentResult

from tuttle.model import Invoice, Project


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

    def delete_invoice_by_id(self, invoice_id) -> IntentResult:
        """TODO attempts to delete the invoice associate with the given id
        Return was_intent_successful=True if successful else false with a log_message
        """
        return IntentResult(
            was_intent_successful=False,
            log_message="Un Implemented exception @InvoicingDataSource.delete_invoice_by_id",
        )

    def create_or_update_invoice(
        self, invoice: Invoice, project: Project
    ) -> IntentResult:
        """TODO if provided invoice object has an id, then attempts to update this invoice else creates a new one
        Return the created/updated invoice as data if successul,
        else was_intent_successful=False with a log_message
        """
        return IntentResult(
            was_intent_successful=False,
            log_message="Un Implemented exception @InvoicingDataSource.create_or_update_invoice",
        )

    """TODO --REMOVE THIS COMMENT --- unlike the above usecase, 
    this update method below is used when the project has not changed, 
    only properties of an invoice like the status"""

    def update_invoice(self, invoice):
        """TODO Saves an updated invoice, and returns the updated invoice as data if successful"""
        return IntentResult(
            was_intent_successful=False,
            log_message="Un Implemented error @InvoicingDataSource.update_invoice",
        )
