from typing import List, Optional, Type, Union

import datetime

from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult

from tuttle.model import Invoice, Project


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

    def delete_invoice_by_id(self, invoice_id):
        """Deletes an invoice by id

        Args:
            invoice_id (int): the id of the invoice to delete
        """
        self.delete_by_id(Invoice, invoice_id)

    def save_invoice(
        self,
        invoice: Invoice,
    ):
        """Creates or updates an invoice with given invoice and project info"""
        self.store(invoice)

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
