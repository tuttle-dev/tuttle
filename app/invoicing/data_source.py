from typing import List, Optional

from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult
from tuttle.model import Invoice, Project
import datetime


class InvoicingDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the Invoice model in the database"""

    def __init__(self):
        super().__init__()

    def get_invoices_for_project(self, project_id) -> IntentResult[List[Invoice]]:
        """TODO Get all invoices associated with a given project

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : list[Invoice] was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            return IntentResult(
                was_intent_successful=False,
                log_message="NotImplementedError @InvoicingDataSource.get_invoices_for_project",
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @TimeTrackingDataSource.get_invoices_for_project {e.__class__.__name__}",
                exception=e,
            )

    def get_all_invoices(self) -> IntentResult[List[Invoice]]:
        """Get all existing invoices

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : list[Invoice] was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            invoices = self.query(Invoice)
            return IntentResult(
                was_intent_successful=True,
                data=invoices,
            )
        except Exception as ex:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @InvoicingDataSource.get_all_invoices {ex}",
                exception=ex,
            )

    def delete_invoice_by_id(self, invoice_id) -> IntentResult[None]:
        """TODO Deletes the invoice corresponding to the given id

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            return IntentResult(
                was_intent_successful=False,
                log_message="NotImplementedError @InvoicingDataSource.delete_invoice_by_id",
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @InvoicingDataSource.delete_invoice_by_id {e.__class__.__name__}",
                exception=e,
            )

    def create_or_update_invoice(
        self,
        invoice: Invoice,
        project: Project,
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> IntentResult[Invoice]:
        """TODO Creates or updates an invoice with given invoice and project info

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : Invoice
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            # TODO: do we need project and time_range?
            self.store(invoice)
            return IntentResult(
                was_intent_successful=True,
                log_message="Successfulyl created invoice",
                data=invoice,  # needs to be returned to the intent to obtain the invoice id
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @InvoicingDataSource.create_or_update_invoice {e.__class__.__name__}",
                exception=e,
            )

    def update_invoice(self, invoice: Invoice) -> IntentResult:
        """TODO Updates a given invoice

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : Invoice
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            return IntentResult(
                was_intent_successful=False,
                log_message="NotImplementedError @InvoicingDataSource.update_invoice",
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @InvoicingDataSource.update_invoice {e.__class__.__name__}",
                exception=e,
            )

    def get_last_invoice(self) -> IntentResult[Invoice]:
        """Get the last invoice.

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : Invoice
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            # query the database to get the Invoice that was last added
            with self.create_session() as session:
                last_invoice = (
                    session.query(Invoice).order_by(Invoice.id.desc()).first()
                )
            return IntentResult(
                was_intent_successful=True,
                data=last_invoice,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @InvoicingDataSource.get_last_invoice_number {e.__class__.__name__}",
                exception=e,
            )
