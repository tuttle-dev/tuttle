from typing import Callable, Optional

from datetime import datetime, timedelta

from flet import (
    AlertDialog,
    Column,
    Container,
    ListTile,
    ListView,
    ResponsiveRow,
    Row,
    UserControl,
    icons,
)

from core import utils, views
from core.abstractions import DialogHandler, TView, TViewParams
from core.intent_result import IntentResult
from loguru import logger
from pandas import DataFrame
from res import colors, dimens, fonts, res_utils

from tuttle.model import Invoice, Project, User

from .intent import InvoicingIntent


class InvoicingEditorPopUp(DialogHandler, UserControl):
    """Pop up used for editing or creating an invoice

    Parameters:
        dialog_controller (Callable[[any, utils.AlertDialogControls], None]):
            The dialog controller
        on_submit (Callable):
            function that is called when the "Done" button is clicked
        projects_map (dict):
            a dictionary of projects mapped by their id
        invoice (Invoice, optional):
            an invoice object to edit, defaults to None if a new one is to be created
    """

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_submit: Callable,
        projects_map,
        invoice: Optional[Invoice] = None,
    ):
        # set the dimensions of the pop up
        pop_up_height = dimens.MIN_WINDOW_HEIGHT * 0.9
        pop_up_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)

        # initialize the data
        today = datetime.today()
        yesterday = datetime.now() - timedelta(1)
        is_editing = invoice is not None
        self.invoice = invoice if is_editing else Invoice(number="", date=today)
        self.projects_as_map = projects_map
        project_options = [
            f"{id} {project.title}".strip()
            for id, project in self.projects_as_map.items()
        ]
        title = "Edit Invoice" if is_editing else "New Invoice"
        self.date_field = views.DateSelector(
            label="Invoice Date",
            initial_date=self.invoice.date,
        )
        self.from_date_field = views.DateSelector(
            label="From", initial_date=yesterday, label_color=colors.GRAY_COLOR
        )
        self.to_date_field = views.DateSelector(
            label="To", initial_date=today, label_color=colors.GRAY_COLOR
        )
        self.projects_dropdown = views.TDropDown(
            on_change=self.on_project_selected,
            label="Select project",
            items=project_options,
            show=not is_editing,
        )
        dialog = AlertDialog(
            content=Container(
                height=pop_up_height,
                width=pop_up_width,
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.THeading(title=title, size=fonts.HEADLINE_4_SIZE),
                        views.Spacer(xs_space=True),
                        views.TTextField(
                            label="Invoice Number",
                            hint=self.invoice.number,
                            initial_value=self.invoice.number,
                            keyboard_type=utils.KEYBOARD_NONE,
                            show=is_editing,
                        ),
                        views.Spacer(xs_space=True),
                        self.date_field,
                        views.Spacer(xs_space=True),
                        self.projects_dropdown,
                        views.Spacer(),
                        views.TBodyText(txt="Date range"),
                        self.from_date_field,
                        self.to_date_field,
                        views.Spacer(xs_space=True),
                    ],
                ),
            ),
            actions=[
                views.TPrimaryButton(label="Done", on_click=self.on_submit_btn_clicked),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.project = self.invoice.project if is_editing else None
        self.on_submit = on_submit

    def on_project_selected(self, e):
        selected_project = e.control.value
        # extract id from selected text
        id_ = int(selected_project.split(" ")[0])
        if id_ in self.projects_as_map:
            self.project = self.projects_as_map[id_]

    def on_submit_btn_clicked(self, e):
        """Called when the "Done" button is clicked"""
        date = self.date_field.get_date()
        if date:
            self.invoice.date = date
        from_date: Optional[datetime.date] = self.from_date_field.get_date()
        to_date: Optional[datetime.date] = self.to_date_field.get_date()
        self.close_dialog()
        self.on_submit(self.invoice, self.project, from_date, to_date)


class InvoicingListView(TView, UserControl):
    """The view for displaying the list of invoices"""

    def __init__(self, params: TViewParams):
        super().__init__(params=params)
        self.intent = InvoicingIntent(client_storage=params.client_storage)
        self.invoices_to_display = {}
        self.contacts = {}
        self.active_projects = {}
        self.editor = None
        self.time_tracking_data: DataFrame = None
        self.user: User = None

    def load_user_data(
        self,
    ):
        """Loads the user for payment info"""
        user_result: IntentResult = self.intent.get_user()
        if user_result.was_intent_successful:
            self.user: User = user_result.data
            self.is_user_missing_payment_info()
        else:
            self.show_snack(
                "Something went wrong! Failed to load your info.",
                is_error=True,
            )

    def is_user_missing_payment_info(
        self,
    ):
        """Checks if the user has set up their payment info.
        Displays a snack if they haven't."""
        if not self.user.VAT_number:
            self.show_snack(
                "You have not set up your VAT number yet. "
                "Please do so in the profile section",
                is_error=True,
            )
            return True
        if self.user.bank_account_not_set:
            self.show_snack(
                "You have not set up your payment information yet. "
                "Please do so in the profile section",
                is_error=True,
            )
            return True
        return False

    def parent_intent_listener(self, intent: str, data: any):
        """Handles the intent from the parent view"""
        if intent == res_utils.CREATE_INVOICE_INTENT:
            # create a new invoice
            if self.is_user_missing_payment_info():
                return  # can't create invoice without payment info
            if self.time_tracking_data is None:
                self.show_snack(
                    "You need to import time tracking data before invoices can be created.",
                    is_error=True,
                )
                return  # can't create invoice without time tracking data
            if self.editor is not None:
                self.editor.close_dialog()
            self.editor = InvoicingEditorPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=self.on_save_invoice,
                projects_map=self.active_projects,
            )
            self.editor.open_dialog()

        elif intent == res_utils.RELOAD_INTENT:
            # reload the data
            self.initialize_data()

    def refresh_invoices(self):
        """Refreshes the invoices"""
        self.invoices_list_control.controls.clear()
        for key in self.invoices_to_display:
            try:
                invoice = self.invoices_to_display[key]
                invoiceItemControl = InvoiceTile(
                    invoice=invoice,
                    on_delete_clicked=self.on_delete_invoice_clicked,
                    on_mail_invoice=self.on_mail_invoice,
                    on_view_invoice=self.on_view_invoice,
                    on_view_timesheet=self.on_view_timesheet,
                    toggle_paid_status=self.toggle_paid_status,
                    toggle_cancelled_status=self.toggle_cancelled_status,
                    toggle_sent_status=self.toggle_sent_status,
                )
            except Exception as ex:
                logger.error(f"Error while refreshing invoice: {ex}")
                logger.exception(ex)
                invoiceItemControl = ListTile(
                    title="Error while refreshing invoice",
                )
            finally:
                self.invoices_list_control.controls.append(invoiceItemControl)

    def on_mail_invoice(self, invoice: Invoice):
        """Called when the user clicks send in the context menu of an invoice"""
        result = self.intent.send_invoice_by_mail(invoice)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)

    def on_view_invoice(self, invoice: Invoice):
        """Called when the user clicks view in the context menu of an invoice"""
        result = self.intent.view_invoice(invoice)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)

    def on_view_timesheet(self, invoice: Invoice):
        """Called when the user clicks view in the context menu of an invoice"""
        result = self.intent.view_timesheet_for_invoice(invoice)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)

    def on_delete_invoice_clicked(self, invoice: Invoice):
        """Called when the user clicks delete in the context menu of an invoice"""
        if self.editor is not None:
            self.editor.close_dialog()
        self.editor = views.ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description=f"Are you sure you wish to delete this invoice?\nInvoice number: {invoice.number}",
            on_proceed=self.on_delete_confirmed,
            proceed_button_label="Yes! Delete",
            data_on_confirmed=invoice.id,
        )
        self.editor.open_dialog()

    def on_delete_confirmed(self, invoice_id):
        """Called when the user confirms the deletion of an invoice"""
        self.loading_indicator.visible = True
        self.update_self()
        result = self.intent.delete_invoice_by_id(invoice_id)
        is_error = not result.was_intent_successful
        msg = result.error_msg if is_error else "Invoice deleted!"
        self.show_snack(msg, is_error)
        if not is_error and invoice_id in self.invoices_to_display:
            del self.invoices_to_display[invoice_id]
            self.refresh_invoices()
        self.loading_indicator.visible = False
        self.update_self()

    def on_save_invoice(
        self,
        invoice: Invoice,
        project: Project,
        from_date: Optional[datetime.date],
        to_date: Optional[datetime.date],
    ):
        """Called when the user clicks on the submit button in the editor"""
        if not invoice:
            return  # this should never happen

        if not project:
            self.show_snack("Please specify the project")
            return

        if not from_date or not to_date:
            self.show_snack("Please specify the date range")
            return

        if to_date < from_date:
            self.show_snack("The start date cannot be after the end date")
            return

        is_updating = invoice.id is not None
        self.loading_indicator.visible = True
        self.update_self()
        if is_updating:
            # update the invoice
            result: IntentResult = self.intent.update_invoice(invoice=invoice)
        else:
            # create a new invoice
            result: IntentResult = self.intent.create_invoice(
                invoice_date=invoice.date,
                project=project,
                from_date=from_date,
                to_date=to_date,
            )

        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.update_invoice_from_intent_result(result)
            msg = (
                "The invoice has been updated"
                if is_updating
                else "A new invoice has been created"
            )
            self.show_snack(msg, False)
        self.loading_indicator.visible = False
        self.update_self()

    def toggle_paid_status(self, invoice: Invoice):
        """toggle the paid status of the invoice"""
        result: IntentResult = self.intent.toggle_invoice_paid_status(invoice)
        is_error = not result.was_intent_successful
        msg = result.error_msg if is_error else "Invoice status updated."
        self.show_snack(msg, is_error)
        if not is_error and result.data:
            self.update_invoice_from_intent_result(result)
        self.update_self()

    def toggle_sent_status(self, invoice: Invoice):
        """toggle the sent status of the invoice"""
        result: IntentResult = self.intent.toggle_invoice_sent_status(invoice)
        is_error = not result.was_intent_successful
        msg = result.error_msg if is_error else "Invoice status updated."
        self.show_snack(msg, is_error)
        if not is_error and result.data:
            self.update_invoice_from_intent_result(result)
        self.update_self()

    def update_invoice_from_intent_result(self, result: IntentResult[Invoice]):
        """update the invoice from an intent result data"""
        # update the invoice
        updated_invoice: Invoice = result.data
        self.invoices_to_display[updated_invoice.id] = updated_invoice
        self.refresh_invoices()

    def toggle_cancelled_status(self, invoice: Invoice):
        """toggle the cancelled status of the invoice"""
        result: IntentResult = self.intent.toggle_invoice_cancelled_status(invoice)
        is_error = not result.was_intent_successful
        msg = result.error_msg if is_error else "Invoice status updated."
        self.show_snack(msg, is_error)
        if not is_error and result.data:
            self.update_invoice_from_intent_result(result)
        self.update_self()

    def did_mount(self):
        """Called when the view is mounted"""
        self.initialize_data()

    def initialize_data(self):
        """initialize the data for the view"""
        self.mounted = True
        self.loading_indicator.visible = True
        self.active_projects = self.intent.get_active_projects_as_map()
        self.time_tracking_data = self.intent.get_time_tracking_data_as_dataframe()
        self.load_user_data()
        self.invoices_to_display = self.intent.get_all_invoices_as_map()
        count = len(self.invoices_to_display)
        self.loading_indicator.visible = False
        if count == 0:
            self.no_invoices_control.visible = True
        else:
            self.refresh_invoices()
        self.update_self()

    def build(self):
        """build the view"""
        self.loading_indicator = views.TProgressBar()
        self.no_invoices_control = views.TBodyText(
            txt="You have not created any invoices yet",
            show=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.THeading(title="Invoicing", size=fonts.HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.no_invoices_control,
                    ],
                )
            ]
        )
        self.invoices_list_control = ListView(
            expand=False,
            spacing=dimens.SPACE_STD,
        )
        return Column(
            controls=[
                self.title_control,
                views.Spacer(md_space=True),
                Container(self.invoices_list_control, expand=True),
            ],
        )

    def will_unmount(self):
        self.mounted = False
        if self.editor:
            self.editor.dimiss_open_dialogs()


class InvoiceTile(UserControl):
    """
    A UserControl that formats an invoice object as a list tile for display in the UI
    """

    def __init__(
        self,
        invoice: Invoice,
        on_delete_clicked,
        on_mail_invoice,
        on_view_invoice,
        on_view_timesheet,
        toggle_paid_status,
        toggle_sent_status,
        toggle_cancelled_status,
    ):
        super().__init__()
        self.invoice = invoice
        self.on_delete_clicked = on_delete_clicked
        self.on_view_invoice = on_view_invoice
        self.on_view_timesheet = on_view_timesheet
        self.on_mail_invoice = on_mail_invoice
        self.toggle_paid_status = toggle_paid_status
        self.toggle_sent_status = toggle_sent_status
        self.toggle_cancelled_status = toggle_cancelled_status

    def build(self):
        """
        Build and return a ListTile displaying the invoice information
        """
        _project_title = ""
        if self.invoice.project:
            _project_title = self.invoice.project.title
        _currency = ""
        if self.invoice.contract:
            _currency = self.invoice.contract.currency
        _client_name = ""
        if self.invoice.contract and self.invoice.contract.client:
            _client_name = self.invoice.contract.client.name
        return ListTile(
            leading=views.TBodyText(self.invoice.number),
            title=views.TBodyText(f"{_project_title} ➡ {_client_name}"),
            subtitle=Column(
                controls=[
                    views.TBodyText(
                        f'Invoice Date: {self.invoice.date.strftime("%d-%m-%Y")}'
                    ),
                    Row(
                        controls=[
                            views.TBodyText(
                                f"Total: {self.invoice.total:.2f} {_currency}"
                            ),
                            views.TStatusDisplay(txt="Paid", is_done=self.invoice.paid),
                            views.TStatusDisplay(
                                txt="Cancelled", is_done=self.invoice.cancelled
                            ),
                            views.TStatusDisplay(txt="Sent", is_done=self.invoice.sent),
                        ]
                    ),
                ]
            ),
            trailing=views.TContextMenu(
                on_click_delete=lambda e: self.on_delete_clicked(self.invoice),
                prefix_menu_items=[
                    views.TPopUpMenuItem(
                        icon=icons.HOURGLASS_BOTTOM_OUTLINED,
                        txt="Mark as sent"
                        if not self.invoice.sent
                        else "Mark as not sent",
                        on_click=lambda e: self.toggle_sent_status(
                            self.invoice,
                        ),
                    ),
                    views.TPopUpMenuItem(
                        icon=icons.ATTACH_MONEY_OUTLINED,
                        txt="Mark as paid"
                        if not self.invoice.paid
                        else "Mark as not paid",
                        on_click=lambda e: self.toggle_paid_status(self.invoice),
                    ),
                    views.TPopUpMenuItem(
                        icon=icons.CANCEL_OUTLINED,
                        txt="Mark as cancelled"
                        if not self.invoice.cancelled
                        else "Mark as not cancelled",
                        on_click=lambda e: self.toggle_cancelled_status(self.invoice),
                    ),
                    views.TPopUpMenuItem(
                        icon=icons.VISIBILITY_OUTLINED,
                        txt="View",
                        on_click=lambda e: self.on_view_invoice(self.invoice),
                    ),
                    views.TPopUpMenuItem(
                        icon=icons.VISIBILITY_OUTLINED,
                        txt="View Timesheet ",
                        on_click=lambda e: self.on_view_timesheet(self.invoice),
                    ),
                    views.TPopUpMenuItem(
                        icon=icons.OUTGOING_MAIL,
                        txt="Send",
                        on_click=lambda e: self.on_mail_invoice(self.invoice),
                    ),
                ],
            ),
        )
