from typing import Callable, Optional
import datetime
from flet import (
    AlertDialog,
    Card,
    Column,
    Container,
    GridView,
    IconButton,
    ListTile,
    ResponsiveRow,
    Row,
    Text,
    UserControl,
    border_radius,
    icons,
    Icon,
    padding,
    Image,
    ListView,
)

from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from core.intent_result import IntentResult
from core import utils, views

from res import colors, dimens, fonts, res_utils


from tuttle.model import Invoice, Project, InvoiceStatus
from .intent import InvoicingIntent


class InvoicingEditorPopUp(DialogHandler, UserControl):
    """Pop up used for editing or creating an invoice"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_submit: Callable,
        projects_map,
        invoice: Optional[Invoice] = None,
    ):

        self.dialog_height = dimens.MIN_WINDOW_HEIGHT * 0.8
        self.dialog_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)
        self.half_of_dialog_width = int(dimens.MIN_WINDOW_WIDTH * 0.35)

        # initialize the data
        self.invoice = (
            invoice
            if invoice is not None
            else Invoice(number="", date=datetime.date.today())
        )
        self.projects_as_map = projects_map
        project_options = [
            f"{id} {project.title}".strip()
            for id, project in self.projects_as_map.items()
        ]
        title = "Edit Invoice" if invoice is not None else "New Invoice"
        self.date_field = views.DateSelector(
            label="Date", initial_date=self.invoice.date
        )
        dialog = AlertDialog(
            content=Container(
                height=self.dialog_height,
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.get_headline_txt(txt=title, size=fonts.HEADLINE_4_SIZE),
                        views.xsSpace,
                        views.get_std_txt_field(
                            on_change=self.on_number_changed,
                            label="Invoice Number",
                            hint=self.invoice.number,
                            initial_value=self.invoice.number,
                        ),
                        views.xsSpace,
                        views.get_dropdown(
                            on_change=self.on_project_selected,
                            label="Select project",
                            items=project_options,
                        ),
                        views.xsSpace,
                        self.date_field,
                        views.xsSpace,
                    ],
                ),
                width=self.dialog_width,
            ),
            actions=[
                views.get_primary_btn(
                    label="Done", on_click=self.on_submit_btn_clicked
                ),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.number = self.invoice.number
        self.project = None
        self.on_submit = on_submit

    def on_number_changed(self, e):
        self.number = e.control.value

    def on_project_selected(self, e):
        selected_project = e.control.value
        # extract id
        id = selected_project.split(" ")[0]
        if id in self.projects_as_map:
            self.project = self.projects_as_map[id]

    def on_submit_btn_clicked(self, e):
        self.invoice.number = self.number
        date = self.date_field.get_date()
        if date:
            self.invoice.date = date
        self.close_dialog()
        self.on_submit(self.invoice, self.project)


class InvoicingListView(TuttleView, UserControl):
    def __init__(self, params: TuttleViewParams):
        super().__init__(params=params)
        self.intent = InvoicingIntent()
        self.invoices_to_display = {}
        self.contacts = {}
        self.active_projects = {}
        self.editor = None

    def parent_intent_listener(self, intent: str, data: any):
        if intent == res_utils.CREATE_INVOICE_INTENT:
            if self.editor is not None:
                self.editor.close_dialog()
            self.editor = InvoicingEditorPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=self.on_save_invoice,
                projects_map=self.active_projects,
            )
        self.editor.open_dialog()

    def refresh_invoices(self):
        self.invoices_list_control.controls.clear()
        for key in self.invoices_to_display:
            invoice = self.invoices_to_display[key]
            invoiceItemControl = InvoiceTile(
                invoice=invoice,
                on_edit_clicked=self.on_edit_invoice_clicked,
                on_delete_clicked=self.on_delete_invoice_clicked,
                on_mail_invoice=self.on_mail_invoice,
                on_print_invoice=self.on_print_invoice,
                toggle_invoice_status=self.toggle_invoice_status,
            )
            self.invoices_list_control.controls.append(invoiceItemControl)

    def on_edit_invoice_clicked(self, invoice: Invoice):
        if self.editor is not None:
            self.editor.close_dialog()
        self.editor = InvoicingEditorPopUp(
            dialog_controller=self.dialog_controller,
            on_submit=self.on_save_invoice,
            projects_map=self.active_projects,
            invoice=invoice,
        )
        self.editor.open_dialog()

    def on_mail_invoice(self, invoice: Invoice):
        result = self.intent.send_invoice_by_mail_intent(invoice)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)

    def on_print_invoice(self, invoice: Invoice):
        result = self.intent.generate_invoice_doc_intent(invoice)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)

    def on_delete_invoice_clicked(self, invoice: Invoice):
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
        self.loading_indicator.visible = True
        self.update_self()
        result = self.intent.delete_invoice_by_id_intent(invoice_id)
        is_error = not result.was_intent_successful
        msg = result.error_msg if is_error else "Invoice deleted!"
        self.show_snack(msg, is_error)
        if not is_error and invoice_id in self.invoices_to_display:
            del self.invoices_to_display[invoice_id]
            self.refresh_invoices()
        self.loading_indicator.visible = False
        self.update_self()

    def on_save_invoice(self, invoice: Invoice, project: Project):
        is_updating = invoice.id is not None
        self.loading_indicator.visible = True
        self.update_self()
        result: IntentResult = self.intent.save_invoice_intent(invoice, project)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.invoices_to_display[result.data.id] = result.data
            self.refresh_invoices()
            msg = (
                "The invoice has been updated"
                if is_updating
                else "A new invoice has been created"
            )
            self.show_snack(msg, False)
        self.loading_indicator.visible = False
        self.update_self()

    def toggle_invoice_status(self, invoice: Invoice, status_to_toggle: InvoiceStatus):
        self.loading_indicator.visible = True
        self.update_self()
        result: IntentResult = self.intent.toggle_invoice_status_intent(
            invoice, status_to_toggle
        )
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.invoices_to_display[result.data.id] = result.data
            self.refresh_invoices()
            msg = "Invoice status updated."
            self.show_snack(msg, False)
        self.loading_indicator.visible = False
        self.update_self()

    def did_mount(self):
        self.mounted = True
        self.loading_indicator.visible = True
        self.active_projects = self.intent.get_active_projects_as_map_intent()
        self.invoices_to_display = self.intent.get_all_invoices_as_map_intent()
        count = len(self.invoices_to_display)
        self.loading_indicator.visible = False
        if count == 0:
            self.no_invoices_control.visible = True
        else:
            self.refresh_invoices()
        self.update_self()

    def build(self):
        self.loading_indicator = views.horizontal_progress
        self.no_invoices_control = views.get_body_txt(
            txt="You have not created any invoices yet",
            color=colors.ERROR_COLOR,
            show=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.get_headline_txt(
                            txt="Invoicing", size=fonts.HEADLINE_4_SIZE
                        ),
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
                views.mdSpace,
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
        on_edit_clicked,
        on_delete_clicked,
        on_mail_invoice,
        on_print_invoice,
        toggle_invoice_status,
    ):
        super().__init__()
        self.invoice = invoice
        self.on_edit_clicked = on_edit_clicked
        self.on_delete_clicked = on_delete_clicked
        self.on_print_invoice = on_print_invoice
        self.on_mail_invoice = on_mail_invoice
        self.toggle_invoice_status = toggle_invoice_status

    def build(self):
        """
        Build and return a ListTile displaying the invoice information
        """
        return ListTile(
            leading=views.get_body_txt(self.invoice.number),
            title=views.get_body_txt(self.invoice.client.name),
            subtitle=Column(
                controls=[
                    views.get_body_txt(
                        f'Invoice Date: {self.invoice.date.strftime("%d-%m-%Y")}'
                    ),
                    Row(
                        controls=[
                            views.get_body_txt(f"Total: {self.invoice.total}"),
                            views.status_label(txt="Paid", is_done=self.invoice.paid),
                            views.status_label(
                                txt="Cancelled", is_done=self.invoice.cancelled
                            ),
                            views.status_label(txt="Sent", is_done=self.invoice.sent),
                        ]
                    ),
                ]
            ),
            trailing=views.view_edit_delete_pop_up(
                on_click_delete=lambda e: self.on_delete_clicked(self.invoice),
                on_click_edit=lambda e: self.on_edit_clicked(self.invoice),
                prefix_menu_items=[
                    views.pop_up_menu_item(
                        icon=icons.HOURGLASS_BOTTOM_OUTLINED,
                        txt="Mark as sent"
                        if not self.invoice.sent
                        else "Mark as not sent",
                        on_click=lambda e: self.toggle_invoice_status(
                            self.invoice, InvoiceStatus.SENT
                        ),
                    ),
                    views.pop_up_menu_item(
                        icon=icons.ATTACH_MONEY_OUTLINED,
                        txt="Mark as paid"
                        if not self.invoice.paid
                        else "Mark as not paid",
                        on_click=lambda e: self.toggle_invoice_status(
                            self.invoice, InvoiceStatus.PAID
                        ),
                    ),
                    views.pop_up_menu_item(
                        icon=icons.CANCEL_OUTLINED,
                        txt="Mark as cancelled"
                        if not self.invoice.cancelled
                        else "Mark as not cancelled",
                        on_click=lambda e: self.toggle_invoice_status(
                            self.invoice, InvoiceStatus.CANCELLED
                        ),
                    ),
                    views.pop_up_menu_item(
                        icon=icons.OUTGOING_MAIL,
                        txt="Send",
                        on_click=lambda e: self.on_mail_invoice(self.invoice),
                    ),
                    views.pop_up_menu_item(
                        icon=icons.PRINT_OUTLINED,
                        txt="Print",
                        on_click=lambda e: self.on_print_invoice(self.invoice),
                    ),
                ],
            ),
        )
