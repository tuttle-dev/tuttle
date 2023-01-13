"""  """
from loguru import logger
from typing import Mapping
from core.abstractions import IntentResult

from .data_source import InvoicingDataSource
from tuttle.model import Invoice, Project, InvoiceStatus
from projects.intent import ProjectsIntent


class InvoicingIntent:
    def __init__(self):
        self.projects_intent = ProjectsIntent()
        self.data_source = InvoicingDataSource()

    def get_all_projects_as_map(self) -> Mapping[int, Project]:
        """if successful returns a map of active projects"""
        return self.projects_intent.get_active_projects()

    def get_invoices_for_project_as_map(self, project_id) -> IntentResult:
        """returns data as a map of invoices associated with a given project
        or an empty map if none exists"""
        result = self.data_source.get_invoices_for_project(project_id)
        if result.was_intent_successful and result.data:
            invoices_list = result.data
            invoices_map = {invoice.id: invoice for invoice in invoices_list}
            return invoices_map
        else:
            if not result.was_intent_successful:
                logger.error(result.log_message)
                logger.exception(result.exception)
            return {}

    def get_all_invoices_as_map(self) -> Mapping[int, Invoice]:
        """returns data as a map of all invoices in the database"""
        result = self.data_source.get_all_invoices()
        if result.was_intent_successful:
            invoices = result.data
            invoices_map = {invoice.id: invoice for invoice in invoices}
            return invoices_map
        else:
            logger.error(result.log_message)
            logger.exception(result.exception)
            return {}

    def delete_invoice_by_id(self, invoice_id) -> IntentResult:
        result: IntentResult = self.data_source.delete_invoice_by_id(invoice_id)
        if not result.was_intent_successful:
            logger.error(result.log_message)
            logger.exception(result.exception)
            result.error_msg = "Deleting invoice failed! Please retry"
        return result

    def save_invoice(self, invoice: Invoice, project: Project) -> IntentResult:
        """Handles creating or updating an invoice
        if successful returns data as the saved invoice
        """
        result: IntentResult = self.data_source.create_or_update_invoice(
            invoice, project
        )
        if not result.was_intent_successful:
            logger.error(result.log_message)
            logger.exception(result.exception)
            result.error_msg = "failed to save the invoice! Please retry"
        return result

    def mail_an_invoice(self, invoice: Invoice) -> IntentResult:
        """TODO attempts to trigger the mail client to send the intent as attachment"""
        return IntentResult(
            was_intent_successful=False, error_msg="Un Implemented Error"
        )

    def print_an_invoice(self, invoice: Invoice) -> IntentResult:
        """TODO Attempts to generate the invoice as a pdf and open the location"""
        return IntentResult(
            was_intent_successful=False, error_msg="Un Implemented Error"
        )

    def toggle_invoice_status(self, invoice: Invoice, status_to_toggle: InvoiceStatus):
        if status_to_toggle.value == InvoiceStatus.SENT.value:
            invoice.sent = not invoice.sent
        elif status_to_toggle.value == InvoiceStatus.PAID.value:
            invoice.paid = not invoice.paid
        elif status_to_toggle.value == InvoiceStatus.CANCELLED.value:
            invoice.cancelled = not invoice.cancelled
        else:
            return
        result: IntentResult = self.data_source.update_invoice(invoice)
        if not result.was_intent_successful:
            result.error_msg = "Failed to update status of the invoice. Please retry"
            logger.error(result.log_message)
            logger.exception(result.exception)
        return result
