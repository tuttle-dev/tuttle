from typing import Optional

from flet import (
    Card,
    Column,
    Container,
    IconButton,
    ResponsiveRow,
    Row,
    UserControl,
    icons,
    margin,
    padding,
)
from clients.client_model import Client
from core.abstractions import DialogHandler
from clients.views.client_editor import ClientEditorPopUp
from contracts.contract_model import Contract
from contracts.intent_impl import ContractsIntentImpl
from core.abstractions import TuttleView
from core.constants_and_enums import (
    CENTER_ALIGNMENT,
    KEYBOARD_NUMBER,
    SPACE_BETWEEN_ALIGNMENT,
)
from core.models import (
    IntentResult,
    get_cycle_from_value,
    get_cycle_values_as_list,
    get_time_unit_values_as_list,
)
from core.views import (
    DateSelector,
    get_dropdown,
    get_headline_with_subtitle,
    get_primary_btn,
    get_std_txt_field,
    horizontal_progress,
    mdSpace,
    smSpace,
    update_dropdown_items,
)
from res import dimens
from res.dimens import MIN_WINDOW_WIDTH

LABEL_WIDTH = 80


class CreateContractScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        on_navigate_back,
        local_storage,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            on_navigate_back=on_navigate_back,
            horizontal_alignment_in_parent=CENTER_ALIGNMENT,
        )
        self.intent_handler = ContractsIntentImpl(local_storage=local_storage)

        self.loading_indicator = horizontal_progress
        self.new_client_pop_up: Optional[DialogHandler] = None

        # info of contract being edited / created
        self.clients_map = {}
        self.contacts_map = {}
        self.title = ""
        self.client = None
        self.rate = ""
        self.currency = ""
        self.vat_rate = ""
        self.time_unit = None
        self.unit_pw = ""
        self.volume = ""
        self.term_of_payment = ""
        self.billing_cycle = None

    def on_title_changed(self, e):
        self.title = e.control.value

    def on_rate_changed(self, e):
        self.rate = e.control.value

    def on_currency_changed(self, e):
        self.currency = e.control.value

    def on_volume_changed(self, e):
        self.volume = e.control.value

    def on_top_changed(self, e):
        self.term_of_payment = e.control.value

    def on_upw_changed(self, e):
        self.unit_pw = e.control.value

    def on_vat_rate_changed(self, e):
        self.vat_rate = e.control.value

    def on_unit_selected(self, e):
        self.time_unit = e.control.value

    def on_billing_cycle_selected(self, e):
        self.billing_cycle = get_cycle_from_value(e.control.value)

    def clear_title_error(self, e):
        if self.title_field.error_text:
            self.title_field.error_text = None
            self.update()

    def clear_rate_error(self, e):
        if self.rate_field.error_text:
            self.rate_field.error_text = None
            self.update()

    def clear_currency_error(self, e):
        if self.currency_field.error_text:
            self.currency_field.error_text = None
            self.update()

    def clear_volume_error(self, e):
        if self.volume_field.error_text:
            self.volume_field.error_text = None
            self.update()

    def clear_top_error(self, e):
        if self.term_of_payment_field.error_text:
            self.term_of_payment_field.error_text = None
            self.update()

    def clear_upw_error(self, e):
        if self.unit_PW_field.error_text:
            self.unit_PW_field.error_text = None
            self.update()

    def clear_vat_rate_error(self, e):
        if self.vat_rate_field.error_text:
            self.vat_rate_field.error_text = None
            self.update()

    def show_progress_bar_disable_action(self):
        self.loading_indicator.visible = True
        self.submit_btn.disabled = True

    def enable_action_remove_progress_bar(self):
        self.loading_indicator.visible = False
        self.submit_btn.disabled = False

    def did_mount(self):
        self.mounted = True
        self.show_progress_bar_disable_action()
        self.load_clients()
        self.load_contacts()
        self.enable_action_remove_progress_bar()
        if self.mounted:
            self.update()

    def load_clients(self):
        self.clients_map = self.intent_handler.get_all_clients_as_map()
        self.clients_field.error_text = (
            "Please create a new client" if len(self.clients_map) == 0 else None
        )
        update_dropdown_items(self.clients_field, self.get_clients_as_list())

    def load_contacts(self):
        self.contacts_map = self.intent_handler.get_all_contacts_as_map()

    def get_clients_as_list(self):
        """transforms a map of id-client_title to a list for dropdown options"""
        clients = []
        for key in self.clients_map:
            clients.append(self.get_client_dropdown_item(key))
        return clients

    def get_client_dropdown_item(self, key):
        return f"#{key} {self.clients_map[key].title}"

    def on_client_selected(self, e):
        # parse selected value to extract id
        selected = e.control.value
        id = ""
        for c in selected:
            if c == "#":
                continue
            if c == " ":
                break
            id = id + c

        if self.clients_field.error_text:
            self.clients_field.error_text = None
            self.update()
        if int(id) in self.clients_map:
            self.client = self.clients_map[int(id)]

    """ CLIENT POP UP """

    def on_add_client_clicked(self, e):
        if self.new_client_pop_up:
            self.new_client_pop_up.close_dialog()

        self.new_client_pop_up = ClientEditorPopUp(
            dialog_controller=self.dialog_controller,
            on_submit=self.on_client_set_from_pop_up,
            contacts_map=self.contacts_map,
        )
        self.new_client_pop_up.open_dialog()

    def on_client_set_from_pop_up(self, client):
        if client:
            result: IntentResult = self.intent_handler.save_client(client)
            if result.was_intent_successful:
                self.client: Client = result.data
                self.clients_map[self.client.id] = self.client
                update_dropdown_items(self.clients_field, self.get_clients_as_list())
                item = self.get_client_dropdown_item(self.client.id)
                self.clients_field.value = item
            else:
                self.show_snack(result.error_msg, True)
        self.update()

    """ SAVING """

    def on_save(self, e):
        if not self.title:
            self.title_field.error_text = "Contract title is required"
            self.update()
            return

        if self.client is None:
            self.clients_field.error_text = "Please select a client"
            self.update()
            return

        signatureDate = self.signature_date_field.get_date()
        if signatureDate is None:
            self.show_snack("Please specify the signature date", True)
            return

        startDate = self.start_date_field.get_date()
        if startDate is None:
            self.show_snack("Please specify the start date", True)
            return

        endDate = self.end_date_field.get_date()
        if endDate is None:
            self.show_snack("Please specify the end date", True)
            return

        if startDate > endDate:
            self.show_snack(
                "The end date of the contract cannot be before the start date", True
            )
            return

        self.show_progress_bar_disable_action()
        result: IntentResult = self.intent_handler.save_contract(
            title=self.title,
            signature_date=signatureDate,
            start_date=startDate,
            end_date=endDate,
            client=self.client,
            rate=self.rate,
            currency=self.currency,
            VAT_rate=self.vat_rate,
            unit=self.time_unit,
            units_per_workday=self.unit_pw,
            volume=self.volume,
            term_of_payment=self.term_of_payment,
            billing_cycle=self.billing_cycle,
        )
        # TODO add contract if updating
        msg = (
            "New contract created successfully"
            if result.was_intent_successful
            else result.error_msg
        )
        isError = not result.was_intent_successful
        self.enable_action_remove_progress_bar()
        self.show_snack(msg, isError)
        if not isError:
            # re route back
            self.on_navigate_back()

    def build(self):
        self.title_field = get_std_txt_field(
            lbl="Title",
            hint="Contract's title",
            on_change=self.on_title_changed,
            on_focus=self.clear_title_error,
        )
        self.rate_field = get_std_txt_field(
            lbl="Rate",
            hint="Contract's rate",
            on_change=self.on_rate_changed,
            on_focus=self.clear_rate_error,
            keyboard_type=KEYBOARD_NUMBER,
        )
        self.currency_field = get_std_txt_field(
            lbl="Currency",
            hint="Payment currency",
            on_change=self.on_currency_changed,
            on_focus=self.clear_currency_error,
        )
        self.vat_rate_field = get_std_txt_field(
            lbl="Vat",
            hint="Vat rate",
            on_change=self.on_vat_rate_changed,
            on_focus=self.clear_vat_rate_error,
            keyboard_type=KEYBOARD_NUMBER,
        )
        self.unit_PW_field = get_std_txt_field(
            lbl="Units per workday",
            hint="",
            on_change=self.on_upw_changed,
            on_focus=self.clear_upw_error,
            keyboard_type=KEYBOARD_NUMBER,
        )
        self.volume_field = get_std_txt_field(
            lbl="Volume (optional)",
            hint="",
            on_change=self.on_volume_changed,
            on_focus=self.clear_volume_error,
            keyboard_type=KEYBOARD_NUMBER,
        )
        self.term_of_payment_field = get_std_txt_field(
            lbl="Term of payment (optional)",
            hint="",
            on_change=self.on_top_changed,
            on_focus=self.clear_top_error,
            keyboard_type=KEYBOARD_NUMBER,
        )
        self.clients_field = get_dropdown(
            lbl="Client",
            on_change=self.on_client_selected,
            items=self.get_clients_as_list(),
        )
        self.units_field = get_dropdown(
            lbl="Time Unit",
            on_change=self.on_unit_selected,
            items=get_time_unit_values_as_list(),
        )
        self.billing_cycle_field = get_dropdown(
            lbl="Billing Cycle",
            on_change=self.on_billing_cycle_selected,
            items=get_cycle_values_as_list(),
        )
        self.signature_date_field = DateSelector(label="Signed on Date")
        self.start_date_field = DateSelector(label="Start Date")
        self.end_date_field = DateSelector(label="End Date")
        self.submit_btn = get_primary_btn(
            label="Create Contract", on_click=self.on_save
        )
        view = Container(
            expand=True,
            padding=padding.all(dimens.SPACE_MD),
            margin=margin.symmetric(vertical=dimens.SPACE_MD),
            content=Card(
                expand=True,
                content=Container(
                    Column(
                        expand=True,
                        controls=[
                            Row(
                                controls=[
                                    IconButton(
                                        icon=icons.CHEVRON_LEFT_ROUNDED,
                                        on_click=self.on_navigate_back,
                                    ),
                                    get_headline_with_subtitle(
                                        title="New Contract",
                                        subtitle="Create a new contract",
                                    ),
                                ]
                            ),
                            self.loading_indicator,
                            mdSpace,
                            self.title_field,
                            smSpace,
                            self.currency_field,
                            self.rate_field,
                            self.term_of_payment_field,
                            self.unit_PW_field,
                            self.vat_rate_field,
                            self.volume_field,
                            smSpace,
                            Row(
                                alignment=SPACE_BETWEEN_ALIGNMENT,
                                vertical_alignment=CENTER_ALIGNMENT,
                                spacing=dimens.SPACE_STD,
                                controls=[
                                    self.clients_field,
                                    IconButton(
                                        icon=icons.ADD_CIRCLE_OUTLINE,
                                        on_click=self.on_add_client_clicked,
                                    ),
                                ],
                            ),
                            smSpace,
                            self.units_field,
                            smSpace,
                            self.billing_cycle_field,
                            smSpace,
                            self.signature_date_field,
                            smSpace,
                            self.start_date_field,
                            mdSpace,
                            self.end_date_field,
                            mdSpace,
                            self.submit_btn,
                        ],
                    ),
                    padding=padding.all(dimens.SPACE_MD),
                    width=MIN_WINDOW_WIDTH,
                ),
            ),
        )
        return view

    def will_unmount(self):
        try:
            self.mounted = True
            if self.new_client_pop_up:
                self.new_client_pop_up.dimiss_open_dialogs()
        except Exception as e:
            print(e)
