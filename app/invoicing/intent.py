from typing import Mapping, Optional, Union, Type

from pathlib import Path
from datetime import date

from loguru import logger

from core.intent_result import IntentResult
import datetime
from .data_source import InvoicingDataSource
from tuttle.model import Invoice, Project
from projects.intent import ProjectsIntent
from tuttle.os_functions import preview_pdf
from core.abstractions import ClientStorage
from timetracking.intent import TimeTrackingIntent
from pandas import DataFrame


class InvoicingIntent:
    """Handles Invoicing C_R_U_D intents"""

    def __init__(self, local_storage: ClientStorage):
        """
        Attributes
        ----------
        _timetracking_intent : TimeTrackingIntent
            reference to the TimeTrackingIntent for forwarding timetracking related intents
        _data_source : InvoicingDataSource
            reference to the invoicing data source
        _projects_intent : ProjectsIntent
            reference to the ProjectsIntent for forwarding project related intents
        """
        self._timetracking_intent = TimeTrackingIntent(local_storage=local_storage)
        self._projects_intent = ProjectsIntent()
        self._invoicing_data_source = InvoicingDataSource()

    def get_active_projects_as_map(self) -> Mapping[int, Project]:
        return self._projects_intent.get_active_projects_as_map()

    def get_invoices_for_project_as_map(self, project_id) -> IntentResult:
        result = self._invoicing_data_source.get_invoices_for_project(project_id)
        if result.was_intent_successful and result.data:
            invoices_list = result.data
            invoices_map = {invoice.id: invoice for invoice in invoices_list}
            return invoices_map
        else:
            if not result.was_intent_successful:
                result.log_message_if_any()
            return {}

    def get_all_invoices_as_map(self) -> Mapping[int, Invoice]:
        result = self._invoicing_data_source.get_all_invoices()
        if result.was_intent_successful:
            invoices = result.data
            invoices_map = {invoice.id: invoice for invoice in invoices}
            return invoices_map
        else:
            result.log_message_if_any()
            return {}

    def delete_invoice_by_id(self, invoice_id) -> IntentResult[None]:
        result: IntentResult = self._invoicing_data_source.delete_invoice_by_id(
            invoice_id
        )
        if not result.was_intent_successful:
            result.log_message_if_any()
            result.error_msg = "Deleting invoice failed! Please retry"
        return result

    def create_or_update_invoice(
        self,
        invoice_date: date,
        project: Project,
        from_date: date,
        to_date: date,
    ) -> IntentResult[Invoice]:
        """Create a new invoice from time tracking data."""

        # TODO: get the time tracking data
        result = IntentResult()
        if not result.was_intent_successful:
            result.log_message_if_any()
            result.error_msg = "failed to save the invoice! Please retry"
        return result

    def update_invoice(
        self,
        invoice: Invoice,
    ) -> IntentResult:
        result: IntentResult = self._invoicing_data_source.save_invoice(invoice)
        if not result.was_intent_successful:
            result.log_message_if_any()
            result.error_msg = "Failed to update the invoice."
            # TODO re-load old invoice
        return result

    def send_invoice_by_mail(self, invoice: Invoice) -> IntentResult[None]:
        """TODO attempts to trigger the mail client to send the intent as attachment"""
        return IntentResult(was_intent_successful=False, error_msg="Not implemented")

    def generate_invoice_doc(self, invoice: Invoice) -> IntentResult:
        """TODO Attempts to generate the invoice as a pdf and open the location"""
        return IntentResult(was_intent_successful=False, error_msg="Not implemented")

    def toggle_invoice_paid_status(self, invoice: Invoice) -> IntentResult[Invoice]:
        """
        Toggles the "paid" status of an invoice and updates it in the data source.

        Parameters:
            invoice (Invoice):
                The invoice object whose "paid" status will be toggled.

        Returns:
            IntentResult[Invoice]:
                An IntentResult object containing the updated invoice, or old invoice if update was not successful.
        """
        invoice.paid = not invoice.paid
        result: IntentResult = self._invoicing_data_source.save_invoice(invoice)
        if not result.was_intent_successful:
            result.log_message_if_any()
            invoice.paid = not invoice.paid
            result.data = invoice
        return result

    def toggle_invoice_cancelled_status(
        self, invoice: Invoice
    ) -> IntentResult[Invoice]:
        """
        Toggles the "cancelled" status of an invoice and updates it in the data source.

        Parameters:
            invoice (Invoice):
                The invoice object whose "cancelled" status will be toggled.

        Returns:
            IntentResult[Invoice]:
                An IntentResult object containing the updated invoice, or old invoice if update was not successful.
        """
        invoice.cancelled = not invoice.cancelled
        result: IntentResult = self._invoicing_data_source.save_invoice(invoice)
        if not result.was_intent_successful:
            result.log_message_if_any()
            invoice.cancelled = not invoice.cancelled
            result.data = invoice
        return result

    def toggle_invoice_sent_status(self, invoice: Invoice) -> IntentResult[Invoice]:
        """
        Toggles the "sent" status of an invoice and updates it in the data source.

        Parameters:
            invoice (Invoice):
                The invoice object whose "sent" status will be toggled.

        Returns:
            IntentResult[Invoice]:
                An IntentResult object containing the updated invoice, or old invoice if update was not successful.
        """
        invoice.sent = not invoice.sent
        result: IntentResult = self._invoicing_data_source.save_invoice(invoice)
        if not result.was_intent_successful:
            result.log_message_if_any()
            invoice.sent = not invoice.sent
            result.data = invoice
        return result

    def view_invoice(self, invoice: Invoice) -> IntentResult[None]:
        """TODO Attempts to open the invoice in the default pdf viewer"""
        try:
            assert invoice.rendered
            pdf_path = Path().home() / "Invoices" / invoice.file_name
            assert pdf_path.exists()
            preview_pdf(pdf_path)
            return IntentResult(was_intent_successful=True)
        except Exception as ex:
            logger.error(f"Failed to open the invoice: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to open the invoice: {str(ex)}",
            )

    def generate_invoice_number(
        self,
        invoice_date: Optional[date] = None,
    ) -> IntentResult[str]:
        """Creates a unique invoice number"""
        # get the number of the most recent invoice
        result: IntentResult[Invoice] = self._invoicing_data_source.get_last_invoice()
        if result.was_intent_successful:
            last_invoice: Invoice = result.data
            last_invoice_number: str = last_invoice.invoice_number
            # increment the invoice number
            invoice_number = last_invoice_number + 1
            return IntentResult(
                was_intent_successful=True,
                data=f"{invoice_number:05d}",
            )
        else:
            # create the first invoice number
            invoice_number = 1
            return IntentResult(
                was_intent_successful=True,
                data=f"{invoice_number:05d}",
            )

    def get_time_tracking_data_as_dataframe(self) -> Optional[DataFrame]:

        result = self._timetracking_intent.get_timetracking_data()
        return result.data
