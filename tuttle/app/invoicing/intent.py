import datetime as _dt
import textwrap
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Optional

from loguru import logger
from pandas import DataFrame

from ..auth.data_source import UserDataSource
from ..auth.intent import AuthIntent
from ..core.abstractions import Intent
from ..core.intent_result import IntentResult
from ..preferences.intent import PreferencesIntent
from ...data_dir import get_data_dir
from ..preferences.model import (
    DEFAULT_E_INVOICE_PROFILE,
    DEFAULT_INVOICE_NUMBER_SCHEME,
    DEFAULT_INVOICE_TEMPLATE,
    E_INVOICE_PROFILES,
    INVOICE_NUMBER_SCHEMES,
    INVOICE_TEMPLATES,
    PreferencesStorageKeys,
    SUPPORTED_INVOICE_LANGUAGES,
)
from ..projects.intent import ProjectsIntent
from ..timetracking.data_source import TimeTrackingDataFrameSource
from ..timetracking.intent import TimeTrackingIntent
from ...app_db import AppDatabase
from ... import invoicing, mail, rendering, timetracking
from ...model import Invoice, InvoiceItem, Project, Timesheet, User

from .data_source import InvoicingDataSource


class InvoicingIntent(Intent):
    """Invoicing CRUD, creation orchestration, and status toggles."""

    def __init__(self, client_storage=None):
        self._projects_intent = ProjectsIntent()
        self._invoicing_data_source = InvoicingDataSource()
        self._timetracking_data_source = TimeTrackingDataFrameSource()
        self._user_data_source = UserDataSource()
        self._auth_intent = AuthIntent()
        self._preferences_intent = PreferencesIntent()
        self._timetracking_intent = TimeTrackingIntent()

    # -- RPC-facing CRUD -------------------------------------------------------

    def get_all(self) -> IntentResult:
        return self._invoicing_data_source.get_all_invoices()

    def delete(self, id) -> IntentResult:
        return self.delete_invoice_by_id(id)

    def create(
        self,
        project_id,
        invoice_date,
        from_date,
        to_date,
        render=True,
        manual_quantity=None,
        manual_items=None,
        with_timesheet=True,
        notes=None,
    ) -> IntentResult:
        """Orchestrates invoice creation: resolve project, read prefs, delegate."""
        proj_result = self._projects_intent.get_by_id(project_id)
        if not proj_result.was_intent_successful:
            return proj_result
        app_db = AppDatabase()
        language = app_db.get_setting(PreferencesStorageKeys.language_key.value) or "en"
        template_name = (
            app_db.get_setting(PreferencesStorageKeys.invoice_template_key.value)
            or DEFAULT_INVOICE_TEMPLATE
        )
        number_scheme = (
            app_db.get_setting(PreferencesStorageKeys.invoice_number_scheme_key.value)
            or DEFAULT_INVOICE_NUMBER_SCHEME
        )
        e_invoice_profile = (
            app_db.get_setting(PreferencesStorageKeys.e_invoice_profile_key.value)
            or DEFAULT_E_INVOICE_PROFILE
        )

        def _to_date(v):
            return v if isinstance(v, date) else _dt.date.fromisoformat(v)

        return self.create_invoice(
            invoice_date=_to_date(invoice_date),
            project=proj_result.data,
            from_date=_to_date(from_date),
            to_date=_to_date(to_date),
            render=render,
            manual_quantity=manual_quantity,
            manual_items=manual_items,
            language=language,
            template_name=template_name,
            number_scheme=number_scheme,
            with_timesheet=with_timesheet,
            e_invoice_profile=e_invoice_profile or None,
            notes=notes,
        )

    # -- Status toggles (accept id, fetch internally) --------------------------

    def _toggle(self, field: str, invoice_id: int) -> IntentResult:
        result = self._invoicing_data_source.get_invoice_by_id(invoice_id)
        if not result.was_intent_successful or not result.data:
            return IntentResult(
                was_intent_successful=False, error_msg="Invoice not found"
            )
        return getattr(self, f"toggle_invoice_{field}_status")(result.data)

    def send_mail(self, id) -> IntentResult:
        result = self._invoicing_data_source.get_invoice_by_id(id)
        if not result.was_intent_successful or not result.data:
            return IntentResult(
                was_intent_successful=False, error_msg="Invoice not found"
            )
        invoice = result.data
        if invoice.is_reminder:
            return self.send_reminder_by_mail(invoice)
        return self.send_invoice_by_mail(invoice)

    def create_reminder(
        self,
        invoice_id,
        reminder_date,
        new_due_date,
        reminder_fee=None,
    ) -> IntentResult:
        """RPC entry-point for creating a reminder."""

        def _to_date(v):
            return v if isinstance(v, date) else _dt.date.fromisoformat(v)

        app_db = AppDatabase()
        language = app_db.get_setting(PreferencesStorageKeys.language_key.value) or "en"
        template_name = (
            app_db.get_setting(PreferencesStorageKeys.invoice_template_key.value)
            or DEFAULT_INVOICE_TEMPLATE
        )
        fee = Decimal(str(reminder_fee)) if reminder_fee else None
        return self._create_reminder(
            invoice_id=int(invoice_id),
            reminder_date=_to_date(reminder_date),
            new_due_date=_to_date(new_due_date),
            reminder_fee=fee,
            language=language,
            template_name=template_name,
        )

    def toggle_sent(self, id) -> IntentResult:
        return self._toggle("sent", id)

    def toggle_paid(self, id) -> IntentResult:
        return self._toggle("paid", id)

    def toggle_cancelled(self, id) -> IntentResult:
        return self._toggle("cancelled", id)

    # -- Static data -----------------------------------------------------------

    def available_templates(self) -> IntentResult:
        return IntentResult(was_intent_successful=True, data=INVOICE_TEMPLATES)

    def available_languages(self) -> IntentResult:
        return IntentResult(
            was_intent_successful=True, data=SUPPORTED_INVOICE_LANGUAGES
        )

    def available_number_schemes(self) -> IntentResult:
        return IntentResult(was_intent_successful=True, data=INVOICE_NUMBER_SCHEMES)

    def available_e_invoice_profiles(self) -> IntentResult:
        return IntentResult(was_intent_successful=True, data=E_INVOICE_PROFILES)

    def get_user(self) -> IntentResult[User]:
        user = self._user_data_source.get_user()
        return IntentResult(was_intent_successful=True, data=user)

    def get_active_projects_as_map(self) -> Mapping[int, Project]:
        return self._projects_intent.get_active_as_map()

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
        """Delete an invoice by id (cascades to timesheets and invoice items)."""
        try:
            self._invoicing_data_source.delete_invoice_by_id(invoice_id)
            return IntentResult(was_intent_successful=True)
        except Exception as ex:
            logger.error(f"Could not delete invoice with id {invoice_id}: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Could not delete invoice: {ex}",
            )

    def create_invoice(
        self,
        invoice_date: date,
        project: Project,
        from_date: date,
        to_date: date,
        render: bool = True,
        manual_quantity: Optional[float] = None,
        manual_items: Optional[list] = None,
        language: str = "en",
        template_name: Optional[str] = None,
        number_scheme: str = DEFAULT_INVOICE_NUMBER_SCHEME,
        with_timesheet: bool = True,
        e_invoice_profile: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> IntentResult[Invoice]:
        """Create a new invoice.

        When *manual_items* is provided, each entry is a dict with keys
        ``description``, ``quantity``, ``unit``, and ``unit_price``.  The
        VAT rate is taken from the contract.

        When *manual_quantity* is provided (legacy shorthand) the invoice
        is built from that single quantity and the contract rate.

        Otherwise the existing time-tracking flow is used.
        """
        logger.info(f"Creating invoice for {project.title}...")
        user = self._user_data_source.get_user()
        try:
            invoice_number = self._invoicing_data_source.generate_invoice_number(
                invoice_date, scheme=number_scheme
            )

            if manual_items is not None:
                contract = project.contract
                items = [
                    InvoiceItem(
                        start_date=from_date,
                        end_date=to_date,
                        quantity=float(it["quantity"]),
                        unit=it.get(
                            "unit", contract.unit.value if contract.unit else "hour"
                        ),
                        unit_price=it["unit_price"],
                        description=it.get("description", project.title),
                        VAT_rate=contract.VAT_rate,
                        VAT_category=contract.VAT_category,
                    )
                    for it in manual_items
                ]
                invoice = Invoice(
                    date=invoice_date,
                    number=invoice_number,
                    contract=contract,
                    contract_id=contract.id,
                    project=project,
                    project_id=project.id,
                    items=items,
                )
            elif manual_quantity is not None:
                contract = project.contract
                item = InvoiceItem(
                    start_date=from_date,
                    end_date=to_date,
                    quantity=manual_quantity,
                    unit=contract.unit.value if contract.unit else "hour",
                    unit_price=contract.rate,
                    description=project.title,
                    VAT_rate=contract.VAT_rate,
                    VAT_category=contract.VAT_category,
                )
                invoice = Invoice(
                    date=invoice_date,
                    number=invoice_number,
                    contract=contract,
                    contract_id=contract.id,
                    project=project,
                    project_id=project.id,
                    items=[item],
                )
            elif project.contract.is_fixed_price:
                # ── Fixed-price path ──────────────────────────────
                invoice: Invoice = invoicing.generate_fixed_price_invoice(
                    date=invoice_date,
                    number=invoice_number,
                    contract=project.contract,
                    project=project,
                )
            else:
                # ── Time-tracking path (existing) ─────────────────
                timetracking_data = self._timetracking_data_source.get_data_frame()
                timesheet: Timesheet = timetracking.generate_timesheet(
                    timetracking_data,
                    project,
                    from_date,
                    to_date,
                )
                invoice: Invoice = invoicing.generate_invoice(
                    date=invoice_date,
                    number=invoice_number,
                    timesheets=[timesheet],
                    contract=project.contract,
                    project=project,
                )
                timesheet.invoice = invoice

            for item in invoice.items:
                item.validate_vat()
            categories = {item.VAT_category for item in invoice.items}
            if len(categories) > 1:
                # EN16931 BR-O-11/12: category O may not be mixed with any other
                # category. Guarding all mixtures keeps the tax breakdown honest.
                names = ", ".join(sorted(c.value for c in categories))
                error_message = (
                    f"Invoice mixes tax categories ({names}); every item must "
                    "share one category."
                )
                logger.error(error_message)
                return IntentResult(
                    was_intent_successful=False, error_msg=error_message
                )

            if notes:
                invoice.notes = notes.strip() or None

            render_warnings: list[str] = []
            if render:
                if (
                    manual_quantity is None
                    and manual_items is None
                    and with_timesheet
                    and "timesheet" in locals()
                ):
                    try:
                        rendering.render_timesheet(
                            user=user,
                            timesheet=timesheet,
                            out_dir=get_data_dir() / "Timesheets",
                            only_final=True,
                        )
                    except Exception as ex:
                        logger.error(
                            f"Error rendering timesheet for {project.title}: {ex}"
                        )
                        logger.exception(ex)
                        render_warnings.append(
                            f"Timesheet PDF could not be generated: {ex}"
                        )

                resolved_template = template_name or DEFAULT_INVOICE_TEMPLATE
                if not template_name:
                    tmpl_result = (
                        self._preferences_intent.get_preferred_invoice_template()
                    )
                    if tmpl_result.was_intent_successful and tmpl_result.data:
                        resolved_template = tmpl_result.data

                logo_result = self._preferences_intent.get_include_logo()
                resolved_include_logo = (
                    logo_result.data
                    if logo_result.was_intent_successful
                    and logo_result.data is not None
                    else True
                )

                due_date_result = self._preferences_intent.get_include_due_date()
                resolved_include_due_date = (
                    due_date_result.data
                    if due_date_result.was_intent_successful
                    and due_date_result.data is not None
                    else True
                )

                sig_result = self._preferences_intent.get_include_signature()
                resolved_include_signature = (
                    sig_result.data
                    if sig_result.was_intent_successful and sig_result.data is not None
                    else True
                )

                try:
                    rendering.render_invoice(
                        user=user,
                        invoice=invoice,
                        out_dir=get_data_dir() / "Invoices",
                        template_name=resolved_template,
                        only_final=True,
                        language=language,
                        e_invoice_profile=e_invoice_profile,
                        include_logo=resolved_include_logo,
                        include_due_date=resolved_include_due_date,
                        include_signature=resolved_include_signature,
                        accent_color=user.accent_color or "",
                    )
                except Exception as ex:
                    logger.error(f"Error rendering invoice for {project.title}: {ex}")
                    logger.exception(ex)
                    render_warnings.append(f"Invoice PDF could not be generated: {ex}")

            self._invoicing_data_source.save_invoice(invoice)
            warning_msg = "; ".join(render_warnings) if render_warnings else ""
            return IntentResult(
                was_intent_successful=True,
                data=invoice,
                warning=warning_msg,
            )
        except ValueError:
            error_message = (
                f"No time tracking data found for project "
                f"'{project.title}' between {from_date} and {to_date}."
            )
            logger.error(error_message)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_message,
            )
        except Exception as ex:
            logger.error(f"Failed to create invoice: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to create invoice: {ex}",
            )

    def _create_reminder(
        self,
        invoice_id: int,
        reminder_date: date,
        new_due_date: date,
        reminder_fee: Optional[Decimal] = None,
        render: bool = True,
        language: str = "en",
        template_name: Optional[str] = None,
    ) -> IntentResult[Invoice]:
        """Create a payment reminder for an overdue invoice or previous reminder."""
        result = self._invoicing_data_source.get_invoice_by_id(invoice_id)
        if not result.was_intent_successful or not result.data:
            return IntentResult(
                was_intent_successful=False, error_msg="Invoice not found."
            )
        predecessor = result.data

        if predecessor.paid:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Cannot create a reminder for a paid invoice.",
            )
        if predecessor.cancelled:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Cannot create a reminder for a cancelled invoice.",
            )

        try:
            user = self._user_data_source.get_user()
            new_level = predecessor.reminder_level + 1

            # Walk to root via explicit queries to avoid DetachedInstanceError
            root = predecessor
            while root.reminder_for_id is not None:
                parent_result = self._invoicing_data_source.get_invoice_by_id(
                    root.reminder_for_id
                )
                if not parent_result.was_intent_successful or not parent_result.data:
                    break
                root = parent_result.data

            items = [
                InvoiceItem(
                    start_date=item.start_date,
                    end_date=item.end_date,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    description=item.description,
                    VAT_rate=item.VAT_rate,
                    VAT_category=item.VAT_category,
                )
                for item in root.items
            ]

            reminder = Invoice(
                document_type="reminder",
                date=reminder_date,
                number=predecessor.number,
                contract_id=predecessor.contract_id,
                project_id=predecessor.project_id,
                reminder_for_id=predecessor.id,
                reminder_level=new_level,
                reminder_fee=reminder_fee,
                reminder_due_date=new_due_date,
                items=items,
            )

            # Persist first so the reminder gets an id and relationships resolve
            self._invoicing_data_source.save_invoice(reminder)

            # Re-load from DB so all relationships (contract, project, etc.) are hydrated
            reload = self._invoicing_data_source.get_invoice_by_id(reminder.id)
            if reload.was_intent_successful and reload.data:
                reminder = reload.data

            render_warning = ""
            if render:
                resolved_template = template_name or DEFAULT_INVOICE_TEMPLATE
                if not template_name:
                    tmpl_result = (
                        self._preferences_intent.get_preferred_invoice_template()
                    )
                    if tmpl_result.was_intent_successful and tmpl_result.data:
                        resolved_template = tmpl_result.data

                logo_result = self._preferences_intent.get_include_logo()
                resolved_include_logo = (
                    logo_result.data
                    if logo_result.was_intent_successful
                    and logo_result.data is not None
                    else True
                )

                due_date_result = self._preferences_intent.get_include_due_date()
                resolved_include_due_date = (
                    due_date_result.data
                    if due_date_result.was_intent_successful
                    and due_date_result.data is not None
                    else True
                )

                sig_result = self._preferences_intent.get_include_signature()
                resolved_include_signature = (
                    sig_result.data
                    if sig_result.was_intent_successful and sig_result.data is not None
                    else True
                )

                try:
                    rendering.render_invoice(
                        user=user,
                        invoice=reminder,
                        out_dir=get_data_dir() / "Invoices",
                        template_name=resolved_template,
                        only_final=True,
                        language=language,
                        include_logo=resolved_include_logo,
                        include_due_date=resolved_include_due_date,
                        include_signature=resolved_include_signature,
                        accent_color=user.accent_color or "",
                    )
                    self._invoicing_data_source.save_invoice(reminder)
                except Exception as ex:
                    logger.error(f"Error rendering reminder: {ex}")
                    logger.exception(ex)
                    render_warning = f"Reminder PDF could not be generated: {ex}"

            # Final re-load for clean RPC serialization
            final = self._invoicing_data_source.get_invoice_by_id(reminder.id)
            if final.was_intent_successful and final.data:
                reminder = final.data

            return IntentResult(
                was_intent_successful=True,
                data=reminder,
                warning=render_warning,
            )
        except Exception as ex:
            logger.error(f"Failed to create reminder: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to create reminder: {ex}",
            )

    def send_reminder_by_mail(self, invoice: Invoice) -> IntentResult[None]:
        """Compose and open a reminder email in the user's mail client."""
        invoice_path = get_data_dir() / "Invoices" / invoice.file_name
        if not invoice.rendered:
            return IntentResult(
                was_intent_successful=False,
                error_msg="The reminder has not been rendered.",
            )
        if not invoice_path.exists():
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"The reminder file {invoice_path} does not exist.",
            )
        try:
            user = self._user_data_source.get_user()
            client = invoice.contract.client
            contact = client.invoicing_contact if client else None
            greeting = contact.name if contact and contact.name else client.name
            recipient = contact.email if contact and contact.email else None
            if not recipient:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg="No contact email available for this client.",
                )

            level_label = f"{'2nd ' if invoice.reminder_level == 2 else '3rd ' if invoice.reminder_level >= 3 else ''}reminder"
            email_body = textwrap.dedent(
                f"""\
Dear {greeting},

This is a {level_label} regarding the outstanding invoice {invoice.number} for {invoice.project.title}.

Please find attached the payment reminder.

Best regards,
{user.name}"""
            )
            mail.compose_email(
                to=recipient,
                subject=f"Payment Reminder: Invoice {invoice.number}",
                body=email_body,
                attachment_paths=[invoice_path],
            )
            return IntentResult(was_intent_successful=True)
        except Exception as ex:
            logger.error(f"Error sending reminder by mail: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to send the reminder by mail: {ex}",
            )

    def update_invoice(
        self,
        invoice: Invoice,
    ) -> IntentResult:
        result: IntentResult = self._invoicing_data_source.save_invoice(invoice)
        if not result.was_intent_successful:
            result.log_message_if_any()
        return result

    def send_invoice_by_mail(self, invoice: Invoice) -> IntentResult[None]:
        """attempts to trigger the mail client to send the intent as attachment"""
        invoice_path = get_data_dir() / "Invoices" / invoice.file_name
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
            client = invoice.contract.client
            contact = client.invoicing_contact if client else None
            greeting = contact.name if contact and contact.name else client.name
            recipient = contact.email if contact and contact.email else None

            if not recipient:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg="No contact email available for this client.",
                )

            email_body = textwrap.dedent(
                f"""\
Dear {greeting},

Please find attached the invoice for {invoice.project.title}.

Best regards,
{user.name}"""
            )
            mail.compose_email(
                to=recipient,
                subject=f"Invoice {invoice.number}",
                body=email_body,
                attachment_paths=[invoice_path],
            )

            return IntentResult(
                was_intent_successful=True,
            )
        except Exception as ex:
            logger.error(f"Error sending invoice by mail: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to send the invoice by mail: {ex}",
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
            logger.error(f"Error toggling invoice sent status: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to toggle the invoice sent status: {ex}",
            )

    def toggle_invoice_paid_status(self, invoice: Invoice) -> IntentResult[Invoice]:
        """Toggle paid status.  Propagates across the entire reminder chain."""
        try:
            new_paid = not invoice.paid
            chain_result = self._invoicing_data_source.get_reminder_chain(invoice.id)
            if chain_result.was_intent_successful and chain_result.data:
                for inv in chain_result.data:
                    # Re-load each invoice in its own session to avoid detached errors
                    fresh = self._invoicing_data_source.get_invoice_by_id(inv.id)
                    if fresh.was_intent_successful and fresh.data:
                        fresh.data.paid = new_paid
                        self._invoicing_data_source.save_invoice(fresh.data)
            else:
                invoice.paid = new_paid
                self._invoicing_data_source.save_invoice(invoice)
            # Return a fresh copy of the toggled invoice
            result = self._invoicing_data_source.get_invoice_by_id(invoice.id)
            return IntentResult(
                was_intent_successful=True,
                data=result.data if result.was_intent_successful else invoice,
            )
        except Exception as ex:
            logger.error(f"Error toggling invoice paid status: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to toggle the invoice paid status: {ex}",
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
            logger.error(f"Error toggling invoice cancelled status: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to toggle the invoice cancelled status: {ex}",
            )

    def view_invoice(self, invoice: Invoice) -> IntentResult[Path]:
        """Resolve the PDF path for an invoice."""
        if not invoice.rendered:
            return IntentResult(
                was_intent_successful=False,
                error_msg="The invoice has not been rendered.",
            )
        try:
            pdf_path = get_data_dir() / "Invoices" / invoice.file_name
            if not pdf_path.exists():
                return IntentResult(
                    was_intent_successful=False,
                    error_msg=f"Invoice file not found: {pdf_path.name}",
                )
            return IntentResult(was_intent_successful=True, data=pdf_path)
        except Exception as ex:
            error_message = f"Failed to open the invoice: {ex.__class__.__name__}"
            logger.error(error_message)
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_message,
            )

    def view_timesheet_for_invoice(self, id) -> IntentResult[Path]:
        """Resolve the PDF path for the timesheet belonging to an invoice."""
        result = self._invoicing_data_source.get_invoice_by_id(int(id))
        if not result.was_intent_successful or not result.data:
            return IntentResult(
                was_intent_successful=False, error_msg="Invoice not found"
            )
        invoice = result.data
        try:
            timesheet = self._invoicing_data_source.get_timesheet_for_invoice(invoice)
            timesheet_path = get_data_dir() / "Timesheets" / f"{timesheet.prefix}.pdf"
            if not timesheet_path.exists():
                return IntentResult(
                    was_intent_successful=False,
                    error_msg=f"Timesheet file not found: {timesheet_path.name}",
                )
            return IntentResult(was_intent_successful=True, data=timesheet_path)
        except ValueError as ve:
            logger.error(f"Error getting timesheet for invoice: {ve}")
            logger.exception(ve)
            return IntentResult(was_intent_successful=False, error_msg=str(ve))
        except Exception as ex:
            error_message = f"Failed to open the timesheet: {ex.__class__.__name__}"
            logger.error(error_message)
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=error_message,
            )

    def render_timesheet_for_invoice(self, id) -> IntentResult[Invoice]:
        """Post-hoc render of the timesheet PDF for an existing invoice.

        Used when the user opted out of timesheet rendering at create time
        and later requests it from the Timesheet tab.  Fails gracefully for
        manual invoices (no linked timesheet) and for reminders.
        """
        result = self._invoicing_data_source.get_invoice_by_id(int(id))
        if not result.was_intent_successful or not result.data:
            return IntentResult(
                was_intent_successful=False, error_msg="Invoice not found"
            )
        invoice = result.data
        if invoice.is_reminder:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Reminders do not have timesheets.",
            )
        if not invoice.timesheets:
            return IntentResult(
                was_intent_successful=False,
                error_msg="This invoice has no linked timesheet.",
            )
        try:
            user = self._user_data_source.get_user()
            timesheet = invoice.timesheets[0]
            rendering.render_timesheet(
                user=user,
                timesheet=timesheet,
                out_dir=get_data_dir() / "Timesheets",
                only_final=True,
            )
            self._invoicing_data_source.save_timesheet(timesheet)
            reload = self._invoicing_data_source.get_invoice_by_id(invoice.id)
            return IntentResult(
                was_intent_successful=True,
                data=reload.data if reload.was_intent_successful else invoice,
            )
        except Exception as ex:
            logger.error(f"Error rendering timesheet for invoice {id}: {ex}")
            logger.exception(ex)
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to render the timesheet: {ex}",
            )

    def check_rendering(self) -> IntentResult:
        """Verify that the PDF rendering engine is loadable."""
        try:
            import plutoprint  # noqa: F401

            return IntentResult(was_intent_successful=True)
        except Exception as ex:
            logger.error(f"Rendering health check failed: {ex}")
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"PDF rendering unavailable: {ex}",
            )

    def get_time_tracking_data_as_dataframe(self) -> Optional[DataFrame]:

        result = self._timetracking_intent.get_timetracking_data()
        return result.data
