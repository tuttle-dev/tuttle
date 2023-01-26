from typing import Mapping, Optional, Type, Union

import datetime
import textwrap
from datetime import date
from pathlib import Path

from auth.data_source import UserDataSource
from core.abstractions import ClientStorage, Intent
from core.intent_result import IntentResult
from loguru import logger
from pandas import DataFrame
from projects.intent import ProjectsIntent
from timetracking.data_source import TimeTrackingDataFrameSource
from timetracking.intent import TimeTrackingIntent

from tuttle import invoicing, mail, os_functions, rendering, timetracking
from tuttle.model import Invoice, Project, Timesheet, User
from tuttle.os_functions import preview_pdf

from .data_source import InvoicingDataSource
from auth.intent import AuthIntent


class InvoicingIntent(Intent):
    """Handles Invoicing C_R_U_D intents"""

    def __init__(self, client_storage: ClientStorage):
        """
        Attributes
        ----------
        _timetracking_intent : TimeTrackingIntent
            reference to the TimeTrackingIntent for forwarding timetracking related intents
        _data_source : InvoicingDataSource
            reference to the invoicing data source
        _projects_intent : ProjectsIntent
            reference to the ProjectsIntent for forwarding project related intents
        _auth_intent : AuthIntent
            reference to the AuthIntent for forwarding auth related intents
        """
        self._timetracking_intent = TimeTrackingIntent(client_storage=client_storage)
        self._projects_intent = ProjectsIntent()
        self._invoicing_data_source = InvoicingDataSource()
        self._timetracking_data_source = TimeTrackingDataFrameSource()
        self._user_data_source = UserDataSource()
        self._auth_intent = AuthIntent()

    def get_user(self) -> Optional[User]:
        """Get the current user."""
        return self._auth_intent.get_user_if_exists()

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
        """Delete an invoice by id."""
        try:
            self._invoicing_data_source.delete_invoice_by_id(invoice_id)
            return IntentResult(was_intent_successful=True)
        except Exception as ex:
            logger.error(f"Could not delete invoice with id {invoice_id}.")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                message="Could not delete invoice. ",
            )

    def create_invoice(
        self,
        invoice_date: date,
        project: Project,
        from_date: date,
        to_date: date,
        render: bool = True,
    ) -> IntentResult[Invoice]:
        """Create a new invoice from time tracking data."""

        try:
            # get the time tracking data
            timetracking_data = self._timetracking_data_source.get_data_frame()
            timesheet: Timesheet = timetracking.create_timesheet(
                timetracking_data,
                project,
                from_date,
                to_date,
            )

            invoice: Invoice = invoicing.generate_invoice(
                timesheets=[
                    timesheet,
                ],
                contract=project.contract,
                project=project,
                date=invoice_date,
            )

            if render:
                # TODO: render timesheet
                # render invoice
                try:
                    rendering.render_invoice(
                        user=user,
                        invoice=invoice,
                        out_dir=Path.home() / ".tuttle" / "Invoices",
                        only_final=True,
                    )
                    logger.info(f"✅ rendered invoice for {project.title}")
                except Exception as ex:
                    logger.error(f"❌ Error rendering invoice for {project.title}: {ex}")
                    logger.exception(ex)
            # save invoice
            self._invoicing_data_source.save_invoice(invoice)
            return IntentResult(
                was_intent_successful=True,
                data=invoice,
            )
        except ValueError:
            error_message = f"No time tracking data found for project '{project.title}' between {from_date} and {to_date}."
            logger.error(error_message)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_message,
            )
        except Exception as ex:
            error_message = "Failed to create invoice. "
            logger.error(error_message)
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_message,
            )

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
        """attempts to trigger the mail client to send the intent as attachment"""
        invoice_path = Path.home() / ".tuttle" / "Invoices" / invoice.file_name
        if not invoice.rendered:
            return IntentResult(
                was_intent_successful=False,
                error_msg="The invoice has not been rendered.",
            )
        if not invoice_path.exists():
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"The invoice file {invoice_path} does not exist.",
            )
        try:
            user = self._user_data_source.get_user()
            # open email client with message pre-filled
            email_body = f"""
            Dear {invoice.contract.client.invoicing_contact.name},

            Please find attached the invoice for {invoice.project.title}.

            <-- Insert invoice PDF here -->

            Best regards,
            {user.name}
            """
            email_body = textwrap.dedent(email_body)
            mail.compose_email(
                to=invoice.contract.client.invoicing_contact.email,
                subject=f"Invoice {invoice.number}",
                body=email_body,
            )
            # open invoice pdf's folder

            os_functions.open_folder(invoice_path.parent)

            return IntentResult(
                was_intent_successful=True,
            )
        except Exception as ex:
            logger.error(f"❌ Error sending invoice by mail: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to send the invoice by mail. ",
            )

    def generate_invoice_doc(self, invoice: Invoice) -> IntentResult:
        """TODO Attempts to generate the invoice as a pdf and open the location"""
        return IntentResult(was_intent_successful=False, error_msg="Not implemented")

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
        try:
            invoice.sent = not invoice.sent
            self._invoicing_data_source.save_invoice(invoice)
            return IntentResult(
                was_intent_successful=True,
                data=invoice,
            )
        except Exception as ex:
            logger.error(f"❌ Error toggling invoice sent status: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to toggle the invoice sent status. ",
            )

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
        try:
            invoice.paid = not invoice.paid
            self._invoicing_data_source.save_invoice(invoice)
            return IntentResult(
                was_intent_successful=True,
                data=invoice,
            )
        except Exception as ex:
            logger.error(f"❌ Error toggling invoice paid status: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to toggle the invoice paid status. ",
            )

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
        try:
            invoice.cancelled = not invoice.cancelled
            self._invoicing_data_source.save_invoice(invoice)
            return IntentResult(
                was_intent_successful=True,
                data=invoice,
            )
        except Exception as ex:
            logger.error(f"❌ Error toggling invoice cancelled status: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to toggle the invoice cancelled status. ",
            )

    def view_invoice(self, invoice: Invoice) -> IntentResult[None]:
        """Attempts to open the invoice in the default pdf viewer"""
        if not invoice.rendered:
            return IntentResult(
                was_intent_successful=False,
                error_msg="The invoice has not been rendered.",
            )
        try:
            pdf_path = Path().home() / ".tuttle" / "Invoices" / invoice.file_name
            preview_pdf(pdf_path)
            return IntentResult(was_intent_successful=True)
        except Exception as ex:
            # display the execption name in the error message
            error_message = f"Failed to open the invoice: {ex.__class__.__name__}"

            logger.error(error_message)
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_message,
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
