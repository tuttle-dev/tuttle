import typing
from typing import Callable, Mapping, Optional

from flet import (
    Card,
    Column,
    Container,
    IconButton,
    Row,
    UserControl,
    icons,
    margin,
    padding,
)

from core.models import (
    get_cycle_values_as_list,
    get_time_unit_values_as_list,
    get_cycle_from_value,
)
from core.abstractions import LocalCache, TuttleView
from core.views import progress_bars, selectors, texts
from core.views.alert_dialog_controls import AlertDialogControls
from core.views.buttons import get_primary_btn
from core.views.flet_constants import (
    KEYBOARD_NUMBER,
    CENTER_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
)
from core.views.spacers import mdSpace, smSpace
from contracts.contract_intents_impl import ContractIntentImpl
from res import spacing
from res.dimens import MIN_WINDOW_WIDTH
from clients.view.client_creator import NewClientPopUp


class ContractEditorScreen(TuttleView, UserControl):
    def __init__(
        self,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        localCacheHandler: LocalCache,
        onNavigateBack: Callable,
        showSnackCallback: Callable[[str, bool], None],
        pageDialogController: typing.Optional[
            Callable[[any, AlertDialogControls], None]
        ],
    ):
        intentHandler = ContractIntentImpl(cache=localCacheHandler)
        super().__init__(
            onChangeRouteCallback=changeRouteCallback,
            keepBackStack=True,
            horizontalAlignmentInParent=CENTER_ALIGNMENT,
            onNavigateBack=onNavigateBack,
            pageDialogController=pageDialogController,
            intentHandler=intentHandler,
            showSnackCallback=showSnackCallback,
        )
        self.intentHandler = intentHandler
        self.newClientPopUp = NewClientPopUp(
            dialogController=self.pageDialogController,
            onSubmit=self.on_new_client_added,
        )
        self.clients: Mapping[str, str] = {}
        self.contracts: Mapping[str, str] = {}
        self.loadingBar = progress_bars.horizontalProgressBar
        # info of contract being edited / created
        self.contractId: Optional[int] = None
        self.title = ""
        self.clientId = ""
        self.rate = ""
        self.currency = ""
        self.vatRate = ""
        self.timeUnit = None
        self.unitPW = ""
        self.volume = ""
        self.termOfPayment = ""
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
        self.termOfPayment = e.control.value

    def on_upw_changed(self, e):
        self.unitPW = e.control.value

    def on_vat_rate_changed(self, e):
        self.vatRate = e.control.value

    def on_unit_selected(self, e):
        self.timeUnit = e.control.value

    def on_billing_cycle_selected(self, e):
        self.billing_cycle = get_cycle_from_value(e.control.value)

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
        self.clientId = id
        if self.clientsField.error_text:
            self.clientsField.error_text = None
            self.update()

    def clear_title_error(self, e):
        if self.titleField.error_text:
            self.titleField.error_text = None
            self.update()

    def clear_rate_error(self, e):
        if self.rateField.error_text:
            self.rateField.error_text = None
            self.update()

    def clear_currency_error(self, e):
        if self.currencyField.error_text:
            self.currencyField.error_text = None
            self.update()

    def clear_volume_error(self, e):
        if self.volumeField.error_text:
            self.volumeField.error_text = None
            self.update()

    def clear_top_error(self, e):
        if self.termOfPaymentField.error_text:
            self.termOfPaymentField.error_text = None
            self.update()

    def clear_upw_error(self, e):
        if self.unitPWField.error_text:
            self.unitPWField.error_text = None
            self.update()

    def clear_vat_rate_error(self, e):
        if self.vatRateField.error_text:
            self.vatRateField.error_text = None
            self.update()

    def show_progress_bar_disable_action(self):
        self.loadingBar.visible = True
        self.submitButton.disabled = True

    def enable_action_remove_progress_bar(self):
        self.loadingBar.visible = False
        self.submitButton.disabled = False

    def on_new_client_added(self, title: str):
        """attempts to save new client"""
        self.loadingBar.visible = True
        self.submitButton.disabled = True
        result = self.intentHandler.create_client(title)
        if result.wasIntentSuccessful:
            self.reload_load_clients()
        else:
            self.showSnack(result.errorMsg, True)
        self.loadingBar.visible = False
        self.submitButton.disabled = False
        self.update()

    def get_clients_as_list(self):
        """transforms a map of id-client_title to a list for dropdown options"""
        clients = []
        for key in self.clients:
            clients.append(f"#{key} {self.clients[key]}")
        return clients

    def reload_load_clients(self):
        self.clients = self.intentHandler.get_all_clients_as_map()
        self.clientsField.error_text = (
            "Please create a new client" if len(self.clients) == 0 else None
        )
        selectors.update_dropdown_items(self.clientsField, self.get_clients_as_list())

    def did_mount(self):
        self.show_progress_bar_disable_action()
        self.reload_load_clients()
        self.enable_action_remove_progress_bar()
        self.update()

    def on_add_client(self, e):
        self.newClientPopUp.open_dialog()

    def on_save(self, e):
        if self.title is None:
            self.titleField.error_text = "Contract title is required"
            self.update()
            return

        if self.clientId is None:
            self.clientsField.error_text = "Please select a client"
            self.update()
            return

        signatureDate = self.signatureDateField.get_date()
        if signatureDate is None:
            self.showSnack("Please specify the signature date", True)
            return

        startDate = self.startDateField.get_date()
        if startDate is None:
            self.showSnack("Please specify the start date", True)
            return

        endDate = self.endDateField.get_date()
        if endDate is None:
            self.showSnack("Please specify the end date", True)
            return

        if startDate > endDate:
            self.showSnack(
                "The end date of the contract cannot be before the start date", True
            )
            return

        self.show_progress_bar_disable_action()
        result = self.intentHandler.create_or_update_contract(
            title=self.title,
            signature_date=signatureDate,
            start_date=startDate,
            end_date=endDate,
            client_id=self.clientId,
            rate=self.rate,
            currency=self.currency,
            VAT_rate=self.vatRate,
            unit=self.timeUnit,
            units_per_workday=self.unitPW,
            volume=self.volume,
            term_of_payment=self.termOfPayment,
            billing_cycle=self.billing_cycle,
        )
        msg = (
            "New contract created successfully"
            if result.wasIntentSuccessful
            else result.errorMsg
        )
        isError = not result.wasIntentSuccessful
        self.enable_action_remove_progress_bar()
        self.showSnack(msg, isError)

    def build(self):
        self.titleField = texts.get_std_txt_field(
            lbl="Title",
            hint="Contract's title",
            onChangeCallback=self.on_title_changed,
            onFocusCallback=self.clear_title_error,
        )

        self.rateField = texts.get_std_txt_field(
            lbl="Rate (optional)",
            hint="Contract's rate",
            onChangeCallback=self.on_rate_changed,
            onFocusCallback=self.clear_rate_error,
            keyboardType=KEYBOARD_NUMBER,
        )

        self.currencyField = texts.get_std_txt_field(
            lbl="Currency (optional)",
            hint="Payment currency",
            onChangeCallback=self.on_currency_changed,
            onFocusCallback=self.clear_currency_error,
        )

        self.vatRateField = texts.get_std_txt_field(
            lbl="Vat (optional)",
            hint="Vat rate",
            onChangeCallback=self.on_vat_rate_changed,
            onFocusCallback=self.clear_vat_rate_error,
            keyboardType=KEYBOARD_NUMBER,
        )

        self.unitPWField = texts.get_std_txt_field(
            lbl="Units per workday (optional)",
            hint="",
            onChangeCallback=self.on_upw_changed,
            onFocusCallback=self.clear_upw_error,
            keyboardType=KEYBOARD_NUMBER,
        )

        self.volumeField = texts.get_std_txt_field(
            lbl="Volume (optional)",
            hint="",
            onChangeCallback=self.on_volume_changed,
            onFocusCallback=self.clear_volume_error,
            keyboardType=KEYBOARD_NUMBER,
        )

        self.termOfPaymentField = texts.get_std_txt_field(
            lbl="Term of payment (optional)",
            hint="",
            onChangeCallback=self.on_top_changed,
            onFocusCallback=self.clear_top_error,
            keyboardType=KEYBOARD_NUMBER,
        )

        self.clientsField = selectors.get_dropdown(
            lbl="Client",
            onChange=self.on_client_selected,
            items=self.get_clients_as_list(),
        )
        self.unitsField = selectors.get_dropdown(
            lbl="Time Unit",
            onChange=self.on_unit_selected,
            items=get_time_unit_values_as_list(),
        )

        self.billingCycleField = selectors.get_dropdown(
            lbl="Billing Cycle",
            onChange=self.on_billing_cycle_selected,
            items=get_cycle_values_as_list(),
        )

        self.signatureDateField = selectors.DateSelector(label="Signed on Date")
        self.startDateField = selectors.DateSelector(label="Start Date")
        self.endDateField = selectors.DateSelector(label="End Date")
        self.submitButton = get_primary_btn(
            label="Create Contract", onClickCallback=self.on_save
        )
        view = Container(
            expand=True,
            padding=padding.all(spacing.SPACE_MD),
            margin=margin.symmetric(vertical=spacing.SPACE_MD),
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
                                        on_click=self.onNavigateBack,
                                    ),
                                    texts.get_headline_with_subtitle(
                                        title="New Contract",
                                        subtitle="Create a new contract",
                                    ),
                                ]
                            ),
                            self.loadingBar,
                            mdSpace,
                            self.titleField,
                            smSpace,
                            self.currencyField,
                            self.rateField,
                            self.termOfPaymentField,
                            self.unitPWField,
                            self.vatRateField,
                            self.volumeField,
                            smSpace,
                            Row(
                                alignment=SPACE_BETWEEN_ALIGNMENT,
                                vertical_alignment=CENTER_ALIGNMENT,
                                spacing=spacing.SPACE_STD,
                                controls=[
                                    self.clientsField,
                                    IconButton(
                                        icon=icons.ADD_CIRCLE_OUTLINE,
                                        on_click=self.on_add_client,
                                    ),
                                ],
                            ),
                            smSpace,
                            self.unitsField,
                            smSpace,
                            self.billingCycleField,
                            smSpace,
                            self.signatureDateField,
                            smSpace,
                            self.startDateField,
                            mdSpace,
                            self.endDateField,
                            mdSpace,
                            self.submitButton,
                        ],
                    ),
                    padding=padding.all(spacing.SPACE_MD),
                    width=MIN_WINDOW_WIDTH,
                ),
            ),
        )

        return view

    def will_unmount(self):
        try:
            if self.newClientPopUp:
                self.newClientPopUp.dimiss_open_dialogs()
        except Exception as e:
            print(e)
