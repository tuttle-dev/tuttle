import typing
from enum import Enum
from typing import Callable, Optional
from clients.view import ClientEditorPopUp
from res.utils import CONTRACT_EDITOR_SCREEN_ROUTE
from flet import (
    Card,
    Column,
    Container,
    Icon,
    IconButton,
    ResponsiveRow,
    Row,
    Text,
    TextButton,
    UserControl,
    icons,
    padding,
)

from contracts.model import Contract
from contracts.intent import ContractsIntent
from core.abstractions import ClientStorage, TuttleView
from core.constants_and_enums import (
    CENTER_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_JUSTIFY,
    AlertDialogControls,
)
from core.models import IntentResult
from core.views import horizontal_progress, mdSpace
from res import colors, dimens, fonts
from res.dimens import MIN_WINDOW_WIDTH


LABEL_WIDTH = 80

from flet import (
    ButtonStyle,
    Card,
    Column,
    Container,
    ElevatedButton,
    GridView,
    IconButton,
    ResponsiveRow,
    Row,
    Text,
    UserControl,
    border_radius,
    icons,
    margin,
    padding,
)

from clients.model import Client
from contracts.model import Contract
from contracts.intent import ContractsIntent
from core.abstractions import ClientStorage, TuttleView
from core.constants_and_enums import (
    ALWAYS_SCROLL,
    CENTER_ALIGNMENT,
    END_ALIGNMENT,
    HOVERED,
    KEYBOARD_NUMBER,
    OTHER_CONTROL_STATES,
    PRESSED,
    SELECTED,
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
    get_headline_txt,
    get_headline_with_subtitle,
    get_primary_btn,
    get_std_txt_field,
    horizontal_progress,
    mdSpace,
    smSpace,
    update_dropdown_items,
)
from res import dimens
from res.colors import ERROR_COLOR, GRAY_COLOR, PRIMARY_COLOR
from res.dimens import (
    CLICKABLE_PILL_HEIGHT,
    MIN_WINDOW_WIDTH,
    SPACE_MD,
    SPACE_STD,
    SPACE_XS,
)
from res.fonts import BODY_2_SIZE, HEADLINE_4_SIZE, SUBTITLE_1_SIZE

from res.utils import CONTRACT_DETAILS_SCREEN_ROUTE

LABEL_WIDTH = 80


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

from clients.model import Client
from contracts.model import Contract
from contracts.intent import ContractsIntent
from core.abstractions import DialogHandler, TuttleView
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


class ContractCard(UserControl):
    """Formats a single contract info into a card ui display"""

    def __init__(self, contract: Contract, on_click_view: Callable[[str], None]):
        super().__init__()
        self.contract = contract
        self.product_info_container = Column()
        self.on_click_view = on_click_view

    def build(self):
        self.product_info_container.controls = [
            get_headline_txt(txt=self.contract.title, size=SUBTITLE_1_SIZE),
            ResponsiveRow(
                controls=[
                    Text(
                        "Id",
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.contract.id,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        "Client Id",
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.contract.client_id,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        "Billing Cycle",
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.contract.billing_cycle,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        "Start date",
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.contract.get_start_date_as_str(),
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        "End date",
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.contract.get_end_date_as_str(),
                        size=BODY_2_SIZE,
                        color=ERROR_COLOR,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                alignment=END_ALIGNMENT,
                vertical_alignment=END_ALIGNMENT,
                expand=True,
                controls=[
                    ElevatedButton(
                        text="View",
                        on_click=lambda e: self.on_click_view(self.contract.id),
                    ),
                ],
            ),
        ]
        card = Card(
            elevation=2,
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(SPACE_STD),
                border_radius=border_radius.all(12),
                content=self.product_info_container,
            ),
        )
        return card


class ContractEditorScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        on_navigate_back,
        local_storage,
        contract_id: str,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            on_navigate_back=on_navigate_back,
            horizontal_alignment_in_parent=CENTER_ALIGNMENT,
        )
        self.intent_handler = ContractsIntent(local_storage=local_storage)

        self.loading_indicator = horizontal_progress
        self.new_client_pop_up = None

        # info of contract being edited / created
        self.contract_id = contract_id
        self.contract_to_edit: Optional[Contract] = None
        self.clients_map = {}
        self.contacts_map = {}
        self.title = ""
        self.selected_client = None
        self.rate = ""
        self.currency = ""
        self.vat_rate = ""
        self.time_unit = None
        self.unit_PW = ""
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
        self.unit_PW = e.control.value

    def on_vat_rate_changed(self, e):
        self.vat_rate = e.control.value

    def on_unit_selected(self, e):
        self.time_unit = e.control.value

    def on_billing_cycle_selected(self, e):
        self.billing_cycle = get_cycle_from_value(e.control.value)

    def clear_title_error(self, e):
        if self.title_field.error_text:
            self.title_field.error_text = None
            if self.mounted:
                self.update()

    def clear_rate_error(self, e):
        if self.rate_field.error_text:
            self.rate_field.error_text = None
            if self.mounted:
                self.update()

    def clear_currency_error(self, e):
        if self.currency_field.error_text:
            self.currency_field.error_text = None
            if self.mounted:
                self.update()

    def clear_volume_error(self, e):
        if self.volume_field.error_text:
            self.volume_field.error_text = None
            if self.mounted:
                self.update()

    def clear_top_error(self, e):
        if self.termOfPayment_field.error_text:
            self.termOfPayment_field.error_text = None
            if self.mounted:
                self.update()

    def clear_upw_error(self, e):
        if self.unitPW_field.error_text:
            self.unitPW_field.error_text = None
            if self.mounted:
                self.update()

    def clear_vat_rate_error(self, e):
        if self.vatRate_field.error_text:
            self.vatRate_field.error_text = None
            if self.mounted:
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
        self.load_contract()
        self.load_clients()
        self.load_contacts()
        self.enable_action_remove_progress_bar()
        if self.mounted:
            self.update()

    """ LOADING DATA """

    def load_contract(
        self,
    ):
        if self.contract_id is None:
            return
        result = self.intent_handler.get_contract_by_id(self.contract_id)
        if result.was_intent_successful:
            self.contract_to_edit = result.data
        else:
            self.show_snack(
                "Failed to load the contract! Please go back and retry", True
            )

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
            if self.mounted:
                self.update()
        if int(id) in self.clients_map:
            self.selected_client = self.clients_map[int(id)]

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
                self.selected_client: Client = result.data
                self.clients_map[self.selected_client.id] = self.selected_client
                update_dropdown_items(self.clients_field, self.get_clients_as_list())
                item = self.get_client_dropdown_item(self.selected_client.id)
                self.clients_field.value = item
            else:
                self.show_snack(result.error_msg, True)
        if self.mounted:
            self.update()

    """ SAVING """

    def on_save(self, e):
        if not self.title:
            self.title_field.error_text = "Contract title is required"
            self.update()
            return

        if self.selected_client is None:
            self.clients_field.error_text = "Please select a client"
            self.update()
            return

        signatureDate = self.signatureDate_field.get_date()
        if signatureDate is None:
            self.show_snack("Please specify the signature date", True)
            return

        startDate = self.startDate_field.get_date()
        if startDate is None:
            self.show_snack("Please specify the start date", True)
            return

        endDate = self.endDate_field.get_date()
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
            client=self.selected_client,
            rate=self.rate,
            currency=self.currency,
            VAT_rate=self.vat_rate,
            unit=self.time_unit,
            units_per_workday=self.unit_PW,
            volume=self.volume,
            term_of_payment=self.term_of_payment,
            billing_cycle=self.billing_cycle,
            contract=self.contract_to_edit,
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

        self.vatRate_field = get_std_txt_field(
            lbl="Vat",
            hint="Vat rate",
            on_change=self.on_vat_rate_changed,
            on_focus=self.clear_vat_rate_error,
            keyboard_type=KEYBOARD_NUMBER,
        )

        self.unitPW_field = get_std_txt_field(
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

        self.termOfPayment_field = get_std_txt_field(
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

        self.billingCycle_field = get_dropdown(
            lbl="Billing Cycle",
            on_change=self.on_billing_cycle_selected,
            items=get_cycle_values_as_list(),
        )

        self.signatureDate_field = DateSelector(label="Signed on Date")
        self.startDate_field = DateSelector(label="Start Date")
        self.endDate_field = DateSelector(label="End Date")
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
                            self.termOfPayment_field,
                            self.unitPW_field,
                            self.vatRate_field,
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
                            self.billingCycle_field,
                            smSpace,
                            self.signatureDate_field,
                            smSpace,
                            self.startDate_field,
                            mdSpace,
                            self.endDate_field,
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
            self.mounted = False
            if self.new_client_pop_up:
                self.new_client_pop_up.dimiss_open_dialogs()
        except Exception as e:
            print(e)


class ContractStates(Enum):
    ALL = 1
    ACTIVE = 2
    COMPLETED = 3
    UPCOMING = 4


class ContractFiltersView(UserControl):
    """Create and Handles contracts view filtering buttons"""

    def __init__(self, onStateChanged: Callable[[ContractStates], None]):
        super().__init__()
        self.currentState = ContractStates.ALL
        self.stateTofilterButtonsMap = {}
        self.onStateChangedCallback = onStateChanged

    def filter_button(
        self, state: ContractStates, lbl: str, onClick: Callable[[ContractStates], None]
    ):
        button = ElevatedButton(
            text=lbl,
            col={"xs": 6, "sm": 3, "lg": 2},
            on_click=lambda e: onClick(state),
            height=CLICKABLE_PILL_HEIGHT,
            color=PRIMARY_COLOR if state == self.currentState else GRAY_COLOR,
            style=ButtonStyle(
                elevation={
                    PRESSED: 3,
                    SELECTED: 3,
                    HOVERED: 4,
                    OTHER_CONTROL_STATES: 2,
                },
            ),
        )
        return button

    def on_filter_button_clicked(self, state: ContractStates):
        """sets the new state and updates selected button"""
        self.stateTofilterButtonsMap[self.currentState].color = GRAY_COLOR
        self.currentState = state
        self.stateTofilterButtonsMap[self.currentState].color = PRIMARY_COLOR
        self.update()
        self.onStateChangedCallback(state)

    def get_filter_button_lbl(self, state: ContractStates):
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
                lbl=self.get_filter_button_lbl(state),
                state=state,
                onClick=self.on_filter_button_clicked,
            )
            self.stateTofilterButtonsMap[state] = button

    def build(self):
        if len(self.stateTofilterButtonsMap) == 0:
            # set the buttons
            self.set_filter_buttons()

        self.filters = ResponsiveRow(
            controls=list(self.stateTofilterButtonsMap.values())
        )
        return self.filters


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
        self.intent_handler = ContractsIntent(local_storage=local_storage)

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
            if self.mounted:
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


class ContractsListView(TuttleView, UserControl):
    def __init__(self, navigate_to_route, show_snack, dialog_controller, local_storage):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = ContractsIntent(local_storage=local_storage)
        self.loading_indicator = horizontal_progress
        self.no_contracts_control = Text(
            value="You have not added any contracts yet",
            color=ERROR_COLOR,
            visible=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt="My Contracts", size=HEADLINE_4_SIZE),
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
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.contracts_to_display = {}

    def load_all_contracts(self):
        self.contracts_to_display = self.intent_handler.get_all_contracts_as_map()

    def display_currently_filtered_contracts(self):
        self.contracts_container.controls.clear()
        for key in self.contracts_to_display:
            contract = self.contracts_to_display[key]
            contractCard = ContractCard(
                contract=contract, on_click_view=self.on_view_contract_clicked
            )
            self.contracts_container.controls.append(contractCard)

    def on_view_contract_clicked(self, contractId: str):
        self.navigate_to_route(CONTRACT_DETAILS_SCREEN_ROUTE, contractId)

    def on_filter_contracts(self, filterByState: ContractStates):
        if filterByState.value == ContractStates.ACTIVE.value:
            self.contracts_to_display = self.intent_handler.get_active_contracts()
        elif filterByState.value == ContractStates.UPCOMING.value:
            self.contracts_to_display = self.intent_handler.get_upcoming_contracts()
        elif filterByState.value == ContractStates.COMPLETED.value:
            self.contracts_to_display = self.intent_handler.get_completed_contracts()
        else:
            self.contracts_to_display = self.intent_handler.get_all_contracts_as_map()
        self.display_currently_filtered_contracts()
        if self.mounted:
            self.update()

    def show_no_contracts(self):
        self.no_contracts_control.visible = True

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.load_all_contracts()
            count = len(self.contracts_to_display)
            self.loading_indicator.visible = False
            if count == 0:
                self.show_no_contracts()
            else:
                self.display_currently_filtered_contracts()
            if self.mounted:
                self.update()
        except Exception as e:
            # log error
            print(f"exception raised @contracts.did_mount {e}")

    def build(self):
        view = Column(
            controls=[
                self.title_control,
                mdSpace,
                ContractFiltersView(onStateChanged=self.on_filter_contracts),
                mdSpace,
                Container(self.contracts_container, expand=True),
            ]
        )
        return view

    def will_unmount(self):
        self.mounted = False


class ViewContractScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        on_navigate_back,
        local_storage,
        contract_id: str,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            on_navigate_back=on_navigate_back,
        )
        self.intent_handler = ContractsIntent(local_storage=local_storage)
        self.contract_id = contract_id
        self.loading_indicator = horizontal_progress
        self.contract: Optional[Contract] = None

    def display_contract_data(self):
        self.contract_title_control.value = self.contract.title
        self.client_control.value = self.contract.client.title
        self.contract_title_control.value = self.contract.title
        self.start_date_control.value = self.contract.start_date
        self.end_date_control.value = self.contract.end_date
        self.status_control.value = f"Status {self.contract.get_status()}"
        self.billing_cycle_control.value = self.contract.billing_cycle
        self.rate_control.value = self.contract.rate
        self.currency_control.value = self.contract.currency
        self.vat_rate_control.value = self.contract.VAT_rate
        self.unit_control.value = self.contract.unit
        self.units_per_workday_control.value = self.contract.units_per_workday
        self.volume_control.value = self.contract.volume
        self.term_of_payment_control.value = self.contract.term_of_payment
        self.signature_date_control.value = self.contract.signature_date

    def did_mount(self):
        self.mounted = True
        result: IntentResult = self.intent_handler.get_contract_by_id(self.contract_id)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.contract = result.data
            self.display_contract_data()
        self.loading_indicator.visible = False
        if self.mounted:
            self.update()

    def on_view_client_clicked(self, e):
        self.show_snack("Coming soon", False)

    def on_mark_as_complete_clicked(self, e):
        self.show_snack("Coming soon", False)

    def on_edit_clicked(self, e):
        """TODO if self.contract is None:
            # project is not loaded yet
            return
        self.navigate_to_route(CONTRACT_EDITOR_SCREEN_ROUTE, self.contract.id)"""
        self.show_snack("Coming soon", False)

    def on_delete_clicked(self, e):
        self.show_snack("Coming soon", False)

    def get_body_element(self, lbl, control):
        return ResponsiveRow(
            controls=[
                Text(
                    lbl,
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
            vertical_alignment=CENTER_ALIGNMENT,
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
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.rate_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.currency_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.vat_rate_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.unit_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.units_per_workday_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.volume_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.term_of_payment_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )

        self.signature_date_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.start_date_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.end_date_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )

        self.status_control = Text(size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR)

        page_view = Row(
            [
                Container(
                    padding=padding.all(dimens.SPACE_STD),
                    width=int(MIN_WINDOW_WIDTH * 0.3),
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
                                                vertical_alignment=CENTER_ALIGNMENT,
                                                alignment=SPACE_BETWEEN_ALIGNMENT,
                                                controls=[
                                                    Text(
                                                        "Contract",
                                                        size=fonts.HEADLINE_4_SIZE,
                                                        font_family=fonts.HEADLINE_FONT,
                                                        color=colors.PRIMARY_COLOR,
                                                    ),
                                                    Row(
                                                        vertical_alignment=CENTER_ALIGNMENT,
                                                        alignment=SPACE_BETWEEN_ALIGNMENT,
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
                            mdSpace,
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
                            mdSpace,
                            Row(
                                spacing=dimens.SPACE_STD,
                                run_spacing=dimens.SPACE_STD,
                                alignment=START_ALIGNMENT,
                                vertical_alignment=CENTER_ALIGNMENT,
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
            alignment=START_ALIGNMENT,
            vertical_alignment=START_ALIGNMENT,
            expand=True,
        )
        return page_view

    def will_unmount(self):
        self.mounted = False