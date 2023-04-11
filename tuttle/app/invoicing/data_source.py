from typing import List, Optional, Type, Union

import datetime

from loguru import logger
import sqlmodel

from ..core.abstractions import SQLModelDataSourceMixin
from ..core.intent_result import IntentResult

from ...model import Invoice, Project, Timesheet


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
        logger.info(f"Saving invoice {invoice}")
        self.store(invoice)

    def save_timesheet(self, timesheet: Timesheet):
        """Creates or updates a timesheet"""
        self.store(timesheet)

    def get_timesheet_for_invoice(self, invoice: Invoice) -> Timesheet:
        """Get the timesheet associated with an invoice

        Args:
            invoice (Invoice): the invoice to get the timesheet for

        Returns:
            Optional[Timesheet]: the timesheet associated with the invoice
        """
        if not len(invoice.timesheets) > 0:
            raise ValueError(
                f"invoice {invoice.id} has no timesheets associated with it"
            )
        if len(invoice.timesheets) > 1:
            raise ValueError(
                f"invoice {invoice.id} has more than one timesheet associated with it: {invoice.timesheets}"
            )
        timesheet = invoice.timesheets[0]
        return timesheet

    def generate_invoice_number(self, date: datetime.date) -> str:
        """Generate a new valid invoice number"""
        # invoice number scheme: YYYY-MM-DD-XX
        prefix = date.strftime("%Y-%m-%d")

        # where XX is the number of invoices for the day
        # if there are no invoices for the day, start at 1
        # if there are invoices for the day, start at the last invoice number + 1
        # count the number of invoices for the day
        with self.create_session() as session:
            invoices = session.exec(
                sqlmodel.select(Invoice).where(Invoice.date == date)
            ).all()
            invoice_count = len(invoices)
            if invoice_count == 0:
                return f"{prefix}-01"
            else:
                return f"{prefix}-{invoice_count + 1}"
