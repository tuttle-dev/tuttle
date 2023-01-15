from typing import Mapping

from pathlib import Path
from loguru import logger

from core.intent_result import IntentResult
from core.models import TuttleDateRange
from .data_source import InvoicingDataSource
from tuttle.model import Invoice, Project, InvoiceStatus
from projects.intent import ProjectsIntent
from tuttle.os_functions import preview_pdf


class InvoicingIntent:
    """Handles Invoicing C_R_U_D intents

    Intents handled (Methods)
    ---------------
    toggle_invoice_status_intent
        toggles a status related property of an invoice
    generate_invoice_doc_intent
        generating a pdf document given an invoice
    send_invoice_by_mail_intent
        sending an invoice as attachment via a mail client
    save_invoice_intent
        saving or updating an invoice
    delete_invoice_by_id_intent
        deleting an invoice given it's id
    get_all_invoices_as_map_intent
        fetching all existing invoices as a map of invoice IDs to invoices
    get_invoices_for_project_as_map_intent
        fetching all existing invoices that correspond to a specific project as a map of invoice IDs to invoices
    get_active_projects_as_map_intent
        fetching all currently active projects
    """

    def __init__(self):
        """
        Attributes
        ----------
        _data_source : InvoicingDataSource
            reference to the invoicing data source
        _projects_intent : ProjectsIntent
            reference to the ProjectsIntent for forwarding project related intents
        """
        self._projects_intent = ProjectsIntent()
        self._data_source = InvoicingDataSource()

    def get_active_projects_as_map(self) -> Mapping[int, Project]:
        return self._projects_intent.get_active_projects_as_map()

    def get_invoices_for_project_as_map(self, project_id) -> IntentResult:
        result = self._data_source.get_invoices_for_project(project_id)
        if result.was_intent_successful and result.data:
            invoices_list = result.data
            invoices_map = {invoice.id: invoice for invoice in invoices_list}
            return invoices_map
        else:
            if not result.was_intent_successful:
                result.log_message_if_any()
            return {}

    def get_all_invoices_as_map(self) -> Mapping[int, Invoice]:
        result = self._data_source.get_all_invoices()
        if result.was_intent_successful:
            invoices = result.data
            invoices_map = {invoice.id: invoice for invoice in invoices}
            return invoices_map
        else:
            result.log_message_if_any()
            return {}

    def delete_invoice_by_id(self, invoice_id) -> IntentResult:
        result: IntentResult = self._data_source.delete_invoice_by_id(invoice_id)
        if not result.was_intent_successful:
            result.log_message_if_any()
            result.error_msg = "Deleting invoice failed! Please retry"
        return result

    def save_invoice(
        self,
        invoice: Invoice,
        project: Project,
        time_range: TuttleDateRange,
    ) -> IntentResult:
        invoice.contract = project.contract
        invoice.project = project
        result: IntentResult = self._data_source.create_or_update_invoice(
            invoice, project, time_range
        )
        if not result.was_intent_successful:
            result.log_message_if_any()
            result.error_msg = "failed to save the invoice! Please retry"
        return result

    def send_invoice_by_mail(self, invoice: Invoice) -> IntentResult:
        """TODO attempts to trigger the mail client to send the intent as attachment"""
        return IntentResult(was_intent_successful=False, error_msg="Not implemented")

    def generate_invoice_doc(self, invoice: Invoice) -> IntentResult:
        """TODO Attempts to generate the invoice as a pdf and open the location"""
        return IntentResult(was_intent_successful=False, error_msg="Not implemented")

    def toggle_invoice_status(
        self, invoice: Invoice, status_to_toggle: InvoiceStatus
    ) -> IntentResult:
        if status_to_toggle.value == InvoiceStatus.SENT.value:
            invoice.sent = not invoice.sent
        elif status_to_toggle.value == InvoiceStatus.PAID.value:
            invoice.paid = not invoice.paid
        elif status_to_toggle.value == InvoiceStatus.CANCELLED.value:
            invoice.cancelled = not invoice.cancelled
        else:
            return
        result: IntentResult = self._data_source.update_invoice(invoice)
        if not result.was_intent_successful:
            result.error_msg = "Failed to update status of the invoice. Please retry"
            result.log_message_if_any()
        return result

    def view_invoice(self, invoice: Invoice) -> IntentResult:
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
        return IntentResult(was_intent_successful=False, error_msg="Not implemented")
