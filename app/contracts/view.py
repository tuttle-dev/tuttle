from typing import Callable, Optional

from enum import Enum

from flet import (
    AlertDialog,
    ButtonStyle,
    Card,
    Column,
    Container,
    ElevatedButton,
    GridView,
    Icon,
    IconButton,
    ListTile,
    ResponsiveRow,
    Row,
    Text,
    TextButton,
    UserControl,
    border_radius,
    icons,
    margin,
    padding,
)

from clients.view import ClientEditorPopUp, ClientViewPopUp
from contracts.intent import ContractsIntent
from core import utils, views
from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from core.intent_result import IntentResult
from core.models import (
    get_cycle_from_value,
    get_cycle_values_as_list,
    get_time_unit_from_value,
    get_time_unit_values_as_list,
)
from res import colors, dimens, fonts, res_utils

from tuttle.model import Client, Contract
from tuttle.time import Cycle, TimeUnit

LABEL_WIDTH = 80


class ContractCard(UserControl):
    """Formats a single contract info into a Card ui display"""

    def __init__(
        self, contract: Contract, on_click_view, on_click_edit, on_click_delete
    ):
        super().__init__()
        self.contract = contract
        self.contract_info_container = Column(run_spacing=0, spacing=0)
        self.on_click_view = on_click_view
        self.on_click_edit = on_click_edit
        self.on_click_delete = on_click_delete

    def build(self):
        self.contract_info_container.controls = [
            ListTile(
                leading=Icon(utils.TuttleComponentIcons.contract_icon),
                title=views.get_body_txt(self.contract.title),
                subtitle=views.get_body_txt(
                    self.contract.client.name if self.contract.client else "",
                    color=colors.GRAY_COLOR,
                ),
                trailing=views.view_edit_delete_pop_up(
                    on_click_view=lambda e: self.on_click_view(self.contract.id),
                    on_click_edit=lambda e: self.on_click_edit(self.contract.id),
                    on_click_delete=lambda e: self.on_click_delete(self.contract.id),
                ),
            ),
            views.mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "Rate",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Text(
                        f"{self.contract.rate} {self.contract.currency} / {self.contract.unit}",
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                ],
                spacing=dimens.SPACE_XS,
                run_spacing=0,
                vertical_alignment=utils.CENTER_ALIGNMENT,
            ),
        ]
        return Card(
            elevation=2,
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(dimens.SPACE_STD),
                border_radius=border_radius.all(12),
                content=self.contract_info_container,
            ),
        )


class ContractStates(Enum):
    ALL = 1
    ACTIVE = 2
    COMPLETED = 3
    UPCOMING = 4


class ContractFiltersView(UserControl):
    """Create and Handles contracts view filtering buttons"""

    def __init__(self, onStateChanged: Callable[[ContractStates], None]):
        super().__init__()
        self.current_state = ContractStates.ALL
        self.state_to_filter_btns_map = {}
        self.on_state_changed_callback = onStateChanged

    def filter_button(
        self,
        state: ContractStates,
        label: str,
        onClick: Callable[[ContractStates], None],
    ):
        button = ElevatedButton(
            text=label,
            col={"xs": 6, "sm": 3, "lg": 2},
            on_click=lambda e: onClick(state),
            height=dimens.CLICKABLE_PILL_HEIGHT,
            color=colors.PRIMARY_COLOR
            if state == self.current_state
            else colors.GRAY_COLOR,
            style=ButtonStyle(
                elevation={
                    utils.PRESSED: 3,
                    utils.SELECTED: 3,
                    utils.HOVERED: 4,
                    utils.OTHER_CONTROL_STATES: 2,
                },
            ),
        )
        return button

    def on_filter_button_clicked(self, state: ContractStates):
        """sets the new state and updates selected button"""
        self.state_to_filter_btns_map[self.current_state].color = colors.GRAY_COLOR
        self.current_state = state
        self.state_to_filter_btns_map[self.current_state].color = colors.PRIMARY_COLOR
        self.update()
        self.on_state_changed_callback(state)

    def get_filter_button_label(self, state: ContractStates):
        if state.value == ContractStates.ACTIVE.value:
            return "Active"
        elif state.value == ContractStates.UPCOMING.value:
            return "Upcoming"
        elif state.value == ContractStates.COMPLETED.value:
            return "Completed"
        else:
            return "All"

    def set_filter_buttons(self):
        for state in ContractStates:
            button = self.filter_button(
                label=self.get_filter_button_label(state),
                state=state,
                onClick=self.on_filter_button_clicked,
            )
            self.state_to_filter_btns_map[state] = button

    def build(self):
        if len(self.state_to_filter_btns_map) == 0:
            # set the buttons
            self.set_filter_buttons()

        self.filters = ResponsiveRow(
            controls=list(self.state_to_filter_btns_map.values())
        )
        return self.filters


class ContractEditorScreen(TuttleView, UserControl):
    """Used to edit or create a contract"""

    def __init__(
        self, params: TuttleViewParams, contract_id_if_editing: Optional[str] = False
    ):
        super().__init__(params=params)
        self.horizontal_alignment_in_parent = utils.CENTER_ALIGNMENT
        self.intent = ContractsIntent()
        self.contract_id_if_editing: Optional[str] = contract_id_if_editing
        self.old_contract_if_editing: Optional[Contract] = None
        self.loading_indicator = views.horizontal_progress
        self.new_client_pop_up: Optional[DialogHandler] = None

        # info of contract being edited / created
        self.clients_map = {}
        self.contacts_map = {}
        self.available_currencies = []
        self.title = ""
        self.client = None
        self.rate = ""
        self.currency = ""
        self.vat_rate = ""
        self.time_unit: TimeUnit = None
        self.unit_pw = ""
        self.volume = ""
        self.term_of_payment = ""
        self.billing_cycle: Cycle = None

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
        self.time_unit = get_time_unit_from_value(e.control.value)

    def on_billing_cycle_selected(self, e):
        self.billing_cycle = get_cycle_from_value(e.control.value)

    def clear_ui_field_errors(self, e):
        fields = [
            self.title_ui_field,
            self.rate_ui_field,
            self.currency_ui_field,
            self.volume_ui_field,
            self.term_of_payment_ui_field,
            self.unit_PW_ui_field,
            self.vat_rate_ui_field,
        ]
        for field in fields:
            if field.error_text:
                field.error_text = None
        self.update_self()

    def toggle_progress(self, is_on_going_action: bool):
        """Hides or shows the progress bar and enables or disables the submit btn"""
        self.loading_indicator.visible = is_on_going_action
        self.submit_btn.disabled = is_on_going_action

    def did_mount(self):
        self.mounted = True
        self.toggle_progress(is_on_going_action=True)
        self.load_clients()
        self.load_contacts()
        self.load_currencies()
        # contract_for_update should be loaded last
        self.load_contract_for_update()
        self.toggle_progress(is_on_going_action=False)
        self.update_self()

    def load_contract_for_update(self):
        if not self.contract_id_if_editing:
            return  # a new contract is being created
        result = self.intent.get_contract_by_id(contractId=self.contract_id_if_editing)
        if not result.was_intent_successful or not result.data:
            self.show_snack(result.error_msg)
        self.old_contract_if_editing = result.data
        self.display_with_contract_info()

    def load_currencies(self):
        self.available_currencies = utils.get_currencies_list()
        views.update_dropdown_items(self.currency_ui_field, self.available_currencies)
        result = self.intent.get_preferred_currency_intent(self.local_storage)
        if result.was_intent_successful:
            preferred_currency = result.data
            self.currency_ui_field.value = preferred_currency

    def load_clients(self):
        self.clients_map = self.intent.get_all_clients_as_map()
        self.clients_ui_field.error_text = (
            "Please create a new client" if len(self.clients_map) == 0 else None
        )
        views.update_dropdown_items(
            self.clients_ui_field, self.get_clients_names_as_list()
        )

    def load_contacts(self):
        self.contacts_map = self.intent.get_all_contacts_as_map()

    def get_clients_names_as_list(self):
        """transforms a map of id-client_title to a list for dropdown options"""
        client_names_list = []
        for key in self.clients_map:
            client_names_list.append(self.get_client_dropdown_item(key))
        return client_names_list

    def get_client_dropdown_item(self, client_id):
        if client_id not in self.clients_map:
            return ""
        """prefixes client name with a key {client_id} for display in Ui as dropdown item"""
        return f"#{client_id} {self.clients_map[client_id].name}"

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

        if self.clients_ui_field.error_text:
            self.clients_ui_field.error_text = None
            self.update_self()
        if int(id) in self.clients_map:
            self.client = self.clients_map[int(id)]

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
            result: IntentResult = self.intent.save_client(client)
            if result.was_intent_successful:
                self.client: Client = result.data
                self.clients_map[self.client.id] = self.client
                views.update_dropdown_items(
                    self.clients_ui_field, self.get_clients_names_as_list()
                )
                item = self.get_client_dropdown_item(self.client.id)
                self.clients_ui_field.value = item
                self.clients_ui_field.error_text = None
            else:
                self.show_snack(result.error_msg, True)
            self.update_self()

    def display_with_contract_info(self):
        """initialize form fields with data from old contract"""
        self.title_ui_field.value = self.title = self.old_contract_if_editing.title
        signature_date = self.old_contract_if_editing.signature_date
        self.signature_date_ui_field.set_date(signature_date)
        start_date = self.old_contract_if_editing.start_date
        self.start_date_ui_field.set_date(start_date)
        end_date = self.old_contract_if_editing.end_date
        self.end_date_ui_field.set_date(end_date)
        self.client = self.old_contract_if_editing.client
        self.clients_ui_field.value = self.get_client_dropdown_item(self.client.id)
        self.rate_ui_field.value = self.rate = self.old_contract_if_editing.rate
        self.currency_ui_field.value = (
            self.currency
        ) = self.old_contract_if_editing.currency
        self.vat_rate_ui_field.value = (
            self.vat_rate
        ) = self.old_contract_if_editing.VAT_rate

        self.time_unit = self.old_contract_if_editing.unit
        if self.time_unit:
            self.units_ui_field.value = self.time_unit.value
        self.unit_PW_ui_field.value = (
            self.unit_pw
        ) = self.old_contract_if_editing.units_per_workday
        self.volume_ui_field.value = self.volume = self.old_contract_if_editing.volume
        self.term_of_payment_ui_field.value = (
            self.term_of_payment
        ) = self.old_contract_if_editing.term_of_payment
        self.billing_cycle = self.old_contract_if_editing.billing_cycle
        if self.billing_cycle:
            self.billing_cycle_ui_field.value = self.billing_cycle.value
        self.form_title_ui_field.value = "Edit Contract"
        self.submit_btn.text = "Save changes"

    def on_save(self, e):
        if not self.title:
            self.title_ui_field.error_text = "Contract title is required"
            self.update_self()
            return

        if self.client is None:
            self.clients_ui_field.error_text = "Please select a client"
            self.update_self()
            return

        signatureDate = self.signature_date_ui_field.get_date()
        if signatureDate is None:
            self.show_snack("Please specify the signature date", True)
            return

        startDate = self.start_date_ui_field.get_date()
        if startDate is None:
            self.show_snack("Please specify the start date", True)
            return

        endDate = self.end_date_ui_field.get_date()
        if endDate is None:
            self.show_snack("Please specify the end date", True)
            return

        if startDate > endDate:
            self.show_snack(
                "The end date of the contract cannot be before the start date", True
            )
            return

        self.toggle_progress(is_on_going_action=True)
        result: IntentResult = self.intent.save_contract(
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
            contract_to_update=self.old_contract_if_editing,
        )
        success_msg = (
            "Changes saved"
            if self.contract_id_if_editing
            else "New contract created successfully"
        )
        msg = success_msg if result.was_intent_successful else result.error_msg
        isError = not result.was_intent_successful
        self.toggle_progress(is_on_going_action=False)
        self.show_snack(msg, isError)
        if not isError:
            # re route back
            self.on_navigate_back()

    def build(self):
        self.title_ui_field = views.get_std_txt_field(
            label="Title",
            hint="Contract's title",
            on_change=self.on_title_changed,
            on_focus=self.clear_ui_field_errors,
        )
        self.rate_ui_field = views.get_std_txt_field(
            label="Rate",
            hint="Contract's rate",
            on_change=self.on_rate_changed,
            on_focus=self.clear_ui_field_errors,
            keyboard_type=utils.KEYBOARD_NUMBER,
        )
        self.currency_ui_field = views.get_dropdown(
            label="Currency",
            hint="Payment currency",
            on_change=self.on_currency_changed,
            items=self.available_currencies,
        )
        self.vat_rate_ui_field = views.get_std_txt_field(
            label="Vat",
            hint="Vat rate",
            on_change=self.on_vat_rate_changed,
            on_focus=self.clear_ui_field_errors,
            keyboard_type=utils.KEYBOARD_NUMBER,
        )
        self.unit_PW_ui_field = views.get_std_txt_field(
            label="Units per workday",
            hint="",
            on_change=self.on_upw_changed,
            on_focus=self.clear_ui_field_errors,
            keyboard_type=utils.KEYBOARD_NUMBER,
        )
        self.volume_ui_field = views.get_std_txt_field(
            label="Volume (optional)",
            hint="",
            on_change=self.on_volume_changed,
            on_focus=self.clear_ui_field_errors,
            keyboard_type=utils.KEYBOARD_NUMBER,
        )
        self.term_of_payment_ui_field = views.get_std_txt_field(
            label="Term of payment (optional)",
            hint="",
            on_change=self.on_top_changed,
            on_focus=self.clear_ui_field_errors,
            keyboard_type=utils.KEYBOARD_NUMBER,
        )
        self.clients_ui_field = views.get_dropdown(
            label="Client",
            on_change=self.on_client_selected,
            items=self.get_clients_names_as_list(),
        )
        self.units_ui_field = views.get_dropdown(
            label="Time Unit",
            on_change=self.on_unit_selected,
            items=get_time_unit_values_as_list(),
        )
        self.billing_cycle_ui_field = views.get_dropdown(
            label="Billing Cycle",
            on_change=self.on_billing_cycle_selected,
            items=get_cycle_values_as_list(),
        )
        self.signature_date_ui_field = views.DateSelector(label="Signed on Date")
        self.start_date_ui_field = views.DateSelector(label="Start Date")
        self.end_date_ui_field = views.DateSelector(label="End Date")
        self.submit_btn = views.get_primary_btn(
            label="Create Contract", on_click=self.on_save
        )
        self.form_title_ui_field = views.get_headline_txt(
            txt="New Contract",
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
                                    self.form_title_ui_field,
                                ]
                            ),
                            self.loading_indicator,
                            views.mdSpace,
                            self.title_ui_field,
                            views.smSpace,
                            self.currency_ui_field,
                            self.rate_ui_field,
                            self.term_of_payment_ui_field,
                            self.unit_PW_ui_field,
                            self.vat_rate_ui_field,
                            self.volume_ui_field,
                            views.smSpace,
                            Row(
                                alignment=utils.SPACE_BETWEEN_ALIGNMENT,
                                vertical_alignment=utils.CENTER_ALIGNMENT,
                                spacing=dimens.SPACE_STD,
                                controls=[
                                    self.clients_ui_field,
                                    IconButton(
                                        icon=icons.ADD_CIRCLE_OUTLINE,
                                        on_click=self.on_add_client_clicked,
                                    ),
                                ],
                            ),
                            views.smSpace,
                            self.units_ui_field,
                            views.smSpace,
                            self.billing_cycle_ui_field,
                            views.smSpace,
                            self.signature_date_ui_field,
                            views.smSpace,
                            self.start_date_ui_field,
                            views.mdSpace,
                            self.end_date_ui_field,
                            views.mdSpace,
                            self.submit_btn,
                        ],
                    ),
                    padding=padding.all(dimens.SPACE_MD),
                    width=dimens.MIN_WINDOW_WIDTH,
                ),
            ),
        )
        return view

    def will_unmount(self):
        self.mounted = True
        if self.new_client_pop_up:
            self.new_client_pop_up.dimiss_open_dialogs()


class ContractsListView(TuttleView, UserControl):
    def __init__(self, params: TuttleViewParams):
        super().__init__(params)
        self.intent = ContractsIntent()
        self.loading_indicator = views.horizontal_progress
        self.no_contracts_control = Text(
            value="You have not added any contracts yet",
            color=colors.ERROR_COLOR,
            visible=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.get_headline_txt(
                            txt="My Contracts", size=fonts.HEADLINE_4_SIZE
                        ),
                        self.loading_indicator,
                        self.no_contracts_control,
                    ],
                )
            ]
        )
        self.contracts_container = GridView(
            expand=False,
            max_extent=540,
            child_aspect_ratio=1.0,
            spacing=dimens.SPACE_STD,
            run_spacing=dimens.SPACE_MD,
        )
        self.contracts_to_display = {}
        self.pop_up_handler = None

    def display_currently_filtered_contracts(self):
        self.contracts_container.controls.clear()
        for key in self.contracts_to_display:
            contract = self.contracts_to_display[key]
            contractCard = ContractCard(
                contract=contract,
                on_click_view=self.on_view_contract_clicked,
                on_click_edit=self.on_edit_contract_clicked,
                on_click_delete=self.on_delete_contract_clicked,
            )
            self.contracts_container.controls.append(contractCard)

    def on_view_contract_clicked(self, contract_id: str):
        self.navigate_to_route(res_utils.CONTRACT_DETAILS_SCREEN_ROUTE, contract_id)

    def on_edit_contract_clicked(self, contract_id: str):
        self.navigate_to_route(res_utils.CONTRACT_EDITOR_SCREEN_ROUTE, contract_id)

    def on_delete_contract_clicked(self, contract_id: str):
        if contract_id not in self.contracts_to_display:
            return
        contract_title = self.contracts_to_display[contract_id].title
        if self.pop_up_handler:
            self.pop_up_handler.close_dialog()
        self.pop_up_handler = views.ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description=f"Are you sure you wish to delete this contract?\n{contract_title}",
            on_proceed=self.on_delete_contract_confirmed,
            proceed_button_label="Yes! Delete",
            data_on_confirmed=contract_id,
        )
        self.pop_up_handler.open_dialog()

    def on_delete_contract_confirmed(self, contract_id: str):
        self.loading_indicator.visible = True
        self.update_self()
        result = self.intent.delete_contract_by_id(contract_id=contract_id)
        is_error = not result.was_intent_successful
        msg = "Contract deleted!" if not is_error else result.error_msg
        self.show_snack(msg, is_error)
        if not is_error and contract_id in self.contracts_to_display:
            del self.contracts_to_display[contract_id]
            self.display_currently_filtered_contracts()
        self.loading_indicator.visible = False
        self.update_self()

    def on_filter_contracts(self, filterByState: ContractStates):
        if filterByState.value == ContractStates.ACTIVE.value:
            self.contracts_to_display = self.intent.get_active_contracts()
        elif filterByState.value == ContractStates.UPCOMING.value:
            self.contracts_to_display = self.intent.get_upcoming_contracts()
        elif filterByState.value == ContractStates.COMPLETED.value:
            self.contracts_to_display = self.intent.get_completed_contracts()
        else:
            self.contracts_to_display = self.intent.get_all_contracts_as_map()
        self.display_currently_filtered_contracts()
        self.update_self()

    def show_no_contracts(self):
        self.no_contracts_control.visible = True

    def did_mount(self):
        self.mounted = True
        self.initialize_data()

    def on_resume_after_back_pressed(self):
        self.mounted = True
        self.initialize_data()

    def initialize_data(self):
        self.loading_indicator.visible = True
        self.update_self()

        # fetch contracts
        self.contracts_to_display = self.intent.get_all_contracts_as_map(
            reload_cache=True
        )
        count = len(self.contracts_to_display)
        if count == 0:
            self.show_no_contracts()
        else:
            self.display_currently_filtered_contracts()
        self.loading_indicator.visible = False
        self.update_self()

    def build(self):
        view = Column(
            controls=[
                self.title_control,
                views.mdSpace,
                ContractFiltersView(onStateChanged=self.on_filter_contracts),
                views.mdSpace,
                Container(self.contracts_container, expand=True),
            ]
        )
        return view

    def will_unmount(self):
        self.mounted = False
        if self.pop_up_handler:
            self.pop_up_handler.dimiss_open_dialogs()


class ViewContractScreen(TuttleView, UserControl):
    def __init__(
        self,
        params: TuttleViewParams,
        contract_id: str,
    ):
        super().__init__(params)
        self.intent = ContractsIntent()
        self.contract_id = contract_id
        self.loading_indicator = views.horizontal_progress
        self.contract: Optional[Contract] = None
        self.pop_up_handler = None

    def display_contract_data(self):
        self.contract_title_control.value = self.contract.title
        self.client_control.value = (
            self.contract.client.name if self.contract.client else ""
        )
        self.contract_title_control.value = self.contract.title
        self.start_date_control.value = self.contract.start_date
        self.end_date_control.value = self.contract.end_date
        self.status_control.value = f"Status {self.contract.get_status()}"
        self.billing_cycle_control.value = (
            self.contract.billing_cycle.value if self.contract.billing_cycle else ""
        )
        self.rate_control.value = self.contract.rate
        self.currency_control.value = self.contract.currency
        self.vat_rate_control.value = self.contract.VAT_rate
        time_unit = self.contract.unit.value if self.contract.unit else ""
        self.unit_control.value = time_unit
        self.units_per_workday_control.value = (
            f"{self.contract.units_per_workday} {time_unit}"
        )
        self.volume_control.value = f"{self.contract.volume} {time_unit}"
        self.term_of_payment_control.value = f"{self.contract.term_of_payment} days"
        self.signature_date_control.value = self.contract.signature_date

    def did_mount(self):
        self.mounted = True
        result: IntentResult = self.intent.get_contract_by_id(self.contract_id)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.contract = result.data
            self.display_contract_data()
        self.loading_indicator.visible = False
        self.update_self()

    def on_view_client_clicked(self, e):
        if not self.contract or not self.contract.client:
            return
        if self.pop_up_handler:
            self.pop_up_handler.close_dialog()
        self.pop_up_handler = ClientViewPopUp(
            dialog_controller=self.dialog_controller, client=self.contract.client
        )
        self.pop_up_handler.open_dialog()

    def on_mark_as_complete_clicked(self, e):
        self.show_snack("Coming soon", False)

    def on_edit_clicked(self, e):
        if not self.contract:
            return
        self.navigate_to_route(res_utils.CONTRACT_EDITOR_SCREEN_ROUTE, self.contract.id)

    def on_delete_clicked(self, e):
        if self.contract is None:
            return
        if self.pop_up_handler:
            self.pop_up_handler.close_dialog()
        self.pop_up_handler = views.ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description=f"Are you sure you wish to delete this contract?\n{self.contract.title}",
            on_proceed=self.on_delete_confirmed,
            proceed_button_label="Yes! Delete",
            data_on_confirmed=self.contract.id,
        )
        self.pop_up_handler.open_dialog()

    def on_delete_confirmed(self, contract_id):
        result = self.intent.delete_contract_by_id(contract_id)
        is_err = not result.was_intent_successful
        msg = result.error_msg if is_err else "Contract deleted!"
        self.show_snack(msg, is_err)
        if not is_err:
            # go back
            self.on_navigate_back()

    def get_body_element(self, label, control):
        return ResponsiveRow(
            controls=[
                Text(
                    label,
                    color=colors.GRAY_COLOR,
                    size=fonts.BODY_2_SIZE,
                    col={
                        "xs": 12,
                    },
                ),
                control,
            ],
            spacing=dimens.SPACE_XS,
            run_spacing=0,
            vertical_alignment=utils.CENTER_ALIGNMENT,
        )

    def build(self):
        """Called when page is built"""
        self.edit_contract_btn = IconButton(
            icon=icons.EDIT_OUTLINED,
            tooltip="Edit contract",
            on_click=self.on_edit_clicked,
        )
        self.mark_as_complete_btn = IconButton(
            icon=icons.CHECK_CIRCLE_OUTLINE,
            icon_color=colors.PRIMARY_COLOR,
            tooltip="Mark contract as completed",
            on_click=self.on_mark_as_complete_clicked,
        )
        self.delete_contract_btn = IconButton(
            icon=icons.DELETE_OUTLINE_ROUNDED,
            icon_color=colors.ERROR_COLOR,
            tooltip="Delete contract",
            on_click=self.on_delete_clicked,
        )

        self.client_control = Text(
            size=fonts.SUBTITLE_2_SIZE,
        )
        self.contract_title_control = Text(
            size=fonts.SUBTITLE_1_SIZE,
        )
        self.billing_cycle_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.rate_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.currency_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.vat_rate_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.unit_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.units_per_workday_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.volume_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.term_of_payment_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )

        self.signature_date_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.start_date_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )
        self.end_date_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=utils.TXT_ALIGN_JUSTIFY,
        )

        self.status_control = Text(size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR)

        page_view = Row(
            [
                Container(
                    padding=padding.all(dimens.SPACE_STD),
                    width=int(dimens.MIN_WINDOW_WIDTH * 0.3),
                    content=Column(
                        controls=[
                            IconButton(
                                icon=icons.KEYBOARD_ARROW_LEFT,
                                on_click=self.on_navigate_back,
                            ),
                            TextButton(
                                "Client",
                                tooltip="View contract's client",
                                on_click=self.on_view_client_clicked,
                            ),
                        ]
                    ),
                ),
                Container(
                    expand=True,
                    padding=padding.all(dimens.SPACE_MD),
                    content=Column(
                        controls=[
                            self.loading_indicator,
                            Row(
                                controls=[
                                    Icon(icons.HANDSHAKE_ROUNDED),
                                    Column(
                                        expand=True,
                                        spacing=0,
                                        run_spacing=0,
                                        controls=[
                                            Row(
                                                vertical_alignment=utils.CENTER_ALIGNMENT,
                                                alignment=utils.SPACE_BETWEEN_ALIGNMENT,
                                                controls=[
                                                    Text(
                                                        "Contract",
                                                        size=fonts.HEADLINE_4_SIZE,
                                                        font_family=fonts.HEADLINE_FONT,
                                                        color=colors.PRIMARY_COLOR,
                                                    ),
                                                    Row(
                                                        vertical_alignment=utils.CENTER_ALIGNMENT,
                                                        alignment=utils.SPACE_BETWEEN_ALIGNMENT,
                                                        spacing=dimens.SPACE_STD,
                                                        run_spacing=dimens.SPACE_STD,
                                                        controls=[
                                                            self.edit_contract_btn,
                                                            self.mark_as_complete_btn,
                                                            self.delete_contract_btn,
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            self.get_body_element(
                                                "Title",
                                                self.contract_title_control,
                                            ),
                                            self.get_body_element(
                                                "Client", self.client_control
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            views.mdSpace,
                            self.get_body_element(
                                "Billing Cycle", self.billing_cycle_control
                            ),
                            self.get_body_element("Rate", self.rate_control),
                            self.get_body_element("Currency", self.currency_control),
                            self.get_body_element("Vat Rate", self.vat_rate_control),
                            self.get_body_element("Time Unit", self.unit_control),
                            self.get_body_element(
                                "Units per Workday",
                                self.units_per_workday_control,
                            ),
                            self.get_body_element("Volume", self.volume_control),
                            self.get_body_element(
                                "Term of Payment", self.term_of_payment_control
                            ),
                            self.get_body_element(
                                "Signed on Date", self.signature_date_control
                            ),
                            self.get_body_element(
                                "Start Date", self.start_date_control
                            ),
                            self.get_body_element("End Date", self.end_date_control),
                            views.mdSpace,
                            Row(
                                spacing=dimens.SPACE_STD,
                                run_spacing=dimens.SPACE_STD,
                                alignment=utils.START_ALIGNMENT,
                                vertical_alignment=utils.CENTER_ALIGNMENT,
                                controls=[
                                    Card(
                                        Container(
                                            self.status_control,
                                            padding=padding.all(dimens.SPACE_SM),
                                        ),
                                        elevation=2,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
            spacing=dimens.SPACE_XS,
            run_spacing=dimens.SPACE_MD,
            alignment=utils.START_ALIGNMENT,
            vertical_alignment=utils.START_ALIGNMENT,
            expand=True,
        )
        return page_view

    def will_unmount(self):
        self.mounted = False
