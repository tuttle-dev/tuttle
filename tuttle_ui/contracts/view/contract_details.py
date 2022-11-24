import typing
from typing import Callable, Optional
from contracts.contract_model import Contract
from flet import (
    Column,
    Container,
    Card,
    Row,
    Text,
    UserControl,
    icons,
    Icon,
    IconButton,
    padding,
    TextButton,
)

from core.views.progress_bars import horizontalProgressBar
from core.abstractions import LocalCache, TuttleView
from core.views.alert_dialog_controls import AlertDialogControls
from core.views.flet_constants import (
    CENTER_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_JUSTIFY,
)
from core.views.spacers import mdSpace
from contracts.contract_intents_impl import ContractIntentImpl
from res import spacing, fonts, colors
from res.dimens import MIN_WINDOW_WIDTH
from res.strings import (
    CLIENT_ID_LBL,
    CONTRACT_ID_LBL,
    START_DATE,
    END_DATE,
    MARK_AS_COMPLETE,
    VIEW_CLIENT_LBL,
    VIEW_CONTRACT_LBL,
    VIEW_CLIENT_HINT,
    VIEW_CONTRACT_HINT,
    CONTRACT_STATUS_LBL,
    DELETE_CONTRACT,
    EDIT_CONTRACT,
    CONTRACT_LBL,
    CONTRACT_BILLING_CYCLE,
    CONTRACT_STATUS_LBL,
    DELETE_CONTRACT,
    EDIT_CONTRACT,
    CONTRACT_LBL,
    CONTRACT_RATE,
    CONTRACT_CURRENCY,
    CONTRACT_VAT_RATE,
    CONTRACT_UNITS_PER_WORKDAY,
    CONTRACT_VOLUME,
    CONTRACT_TERM_OF_PAYMENT,
    CONTRACT_TIME_UNIT,
    CONTRACT_SIGNATURE_DATE,
)

LABEL_WIDTH = 80


class ContractDetailsScreen(TuttleView, UserControl):
    def __init__(
        self,
        contractId: str,
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
        self.contractId = contractId
        self.intentHandler = intentHandler
        self.loadingIndicator = horizontalProgressBar
        self.contract: Optional[Contract]

    def display_contract_data(self):
        self.contractTitleTxt.value = self.contract.title
        self.clientIdTxt.value = f"{CLIENT_ID_LBL}: {self.contract.client_id}"
        self.contractIdTxt.value = f"{CONTRACT_ID_LBL}: {self.contract.id}"
        self.contractStartDateTxt.value = self.contract.start_date
        self.contractEndDateTxt.value = self.contract.end_date
        self.contractStatusTxt.value = (
            f"{CONTRACT_STATUS_LBL} {self.contract.get_status()}"
        )
        self.contractBillingCycle.value = self.contract.billing_cycle
        self.contractRate.value = self.contract.rate
        self.contractCurrency.value = self.contract.currency
        self.contractVatRate.value = self.contract.VAT_rate
        self.contractUnit.value = self.contract.unit
        self.contractUnitsPerWorkday.value = self.contract.units_per_workday
        self.contractVolume.value = self.contract.volume
        self.contractTermOfPayment.value = self.contract.term_of_payment
        self.contractSignatureDateTxt.value = self.contract.signature_date

    def did_mount(self):
        result = self.intentHandler.get_contract_by_id(self.contractId)
        if not result.wasIntentSuccessful:
            self.showSnack(result.errorMsg, True)
        else:
            self.contract = result.data
            self.display_contract_data()
        self.loadingIndicator.visible = False
        self.update()

    def on_view_client_clicked(self, e):
        self.showSnack("Coming soon", False)

    def on_mark_as_complete_clicked(self, e):
        self.showSnack("Coming soon", False)

    def on_edit_clicked(self, e):
        self.showSnack("Coming soon", False)

    def on_delete_clicked(self, e):
        self.showSnack("Coming soon", False)

    def get_body_element(self, lbl, control):
        return Row(
            controls=[
                Text(
                    lbl,
                    color=colors.GRAY_COLOR,
                    size=fonts.BODY_2_SIZE,
                    width=LABEL_WIDTH,
                ),
                control,
            ],
            spacing=spacing.SPACE_XS,
            run_spacing=0,
            vertical_alignment=CENTER_ALIGNMENT,
        )

    def build(self):
        """Called when page is built"""
        self.editContractBtn = IconButton(
            icon=icons.EDIT_OUTLINED,
            tooltip=EDIT_CONTRACT,
            on_click=self.on_edit_clicked,
        )
        self.markAsCompleteBtn = IconButton(
            icon=icons.CHECK_CIRCLE_OUTLINE,
            icon_color=colors.PRIMARY_COLOR,
            tooltip=MARK_AS_COMPLETE,
            on_click=self.on_mark_as_complete_clicked,
        )
        self.deleteContractBtn = IconButton(
            icon=icons.DELETE_OUTLINE_ROUNDED,
            icon_color=colors.ERROR_COLOR,
            tooltip=DELETE_CONTRACT,
            on_click=self.on_delete_clicked,
        )

        self.contractTitleTxt = Text(size=fonts.SUBTITLE_1_SIZE)
        self.clientIdTxt = Text(
            size=fonts.SUBTITLE_2_SIZE,
            color=colors.GRAY_COLOR,
        )
        self.contractIdTxt = Text(
            size=fonts.SUBTITLE_2_SIZE,
            color=colors.GRAY_COLOR,
        )
        self.contractBillingCycle = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractRate = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractCurrency = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractVatRate = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractUnit = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractUnitsPerWorkday = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractVolume = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractTermOfPayment = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )

        self.contractSignatureDateTxt = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractStartDateTxt = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )
        self.contractEndDateTxt = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )

        self.contractStatusTxt = Text(
            size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR
        )

        page_view = Row(
            [
                Container(
                    padding=padding.all(spacing.SPACE_STD),
                    width=int(MIN_WINDOW_WIDTH * 0.3),
                    content=Column(
                        controls=[
                            IconButton(
                                icon=icons.KEYBOARD_ARROW_LEFT,
                                on_click=self.onNavigateBack,
                            ),
                            TextButton(
                                VIEW_CLIENT_LBL,
                                tooltip=VIEW_CLIENT_HINT,
                                on_click=self.on_view_client_clicked,
                            ),
                        ]
                    ),
                ),
                Container(
                    expand=True,
                    padding=padding.all(spacing.SPACE_MD),
                    content=Column(
                        controls=[
                            self.loadingIndicator,
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
                                                        CONTRACT_LBL,
                                                        size=fonts.HEADLINE_4_SIZE,
                                                        font_family=fonts.HEADLINE_FONT,
                                                        color=colors.PRIMARY_COLOR,
                                                    ),
                                                    Row(
                                                        vertical_alignment=CENTER_ALIGNMENT,
                                                        alignment=SPACE_BETWEEN_ALIGNMENT,
                                                        spacing=spacing.SPACE_STD,
                                                        run_spacing=spacing.SPACE_STD,
                                                        controls=[
                                                            self.editContractBtn,
                                                            self.markAsCompleteBtn,
                                                            self.deleteContractBtn,
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            self.contractTitleTxt,
                                            self.clientIdTxt,
                                            self.contractIdTxt,
                                        ],
                                    ),
                                ],
                            ),
                            mdSpace,
                            self.get_body_element(
                                CONTRACT_BILLING_CYCLE, self.contractBillingCycle
                            ),
                            self.get_body_element(CONTRACT_RATE, self.contractRate),
                            self.get_body_element(
                                CONTRACT_CURRENCY, self.contractCurrency
                            ),
                            self.get_body_element(
                                CONTRACT_VAT_RATE, self.contractVatRate
                            ),
                            self.get_body_element(
                                CONTRACT_TIME_UNIT, self.contractUnit
                            ),
                            self.get_body_element(
                                CONTRACT_UNITS_PER_WORKDAY, self.contractUnitsPerWorkday
                            ),
                            self.get_body_element(CONTRACT_VOLUME, self.contractVolume),
                            self.get_body_element(
                                CONTRACT_TERM_OF_PAYMENT, self.contractTermOfPayment
                            ),
                            self.get_body_element(
                                CONTRACT_SIGNATURE_DATE, self.contractSignatureDateTxt
                            ),
                            self.get_body_element(
                                START_DATE, self.contractStartDateTxt
                            ),
                            self.get_body_element(END_DATE, self.contractEndDateTxt),
                            mdSpace,
                            Row(
                                spacing=spacing.SPACE_STD,
                                run_spacing=spacing.SPACE_STD,
                                alignment=START_ALIGNMENT,
                                vertical_alignment=CENTER_ALIGNMENT,
                                controls=[
                                    Card(
                                        Container(
                                            self.contractStatusTxt,
                                            padding=padding.all(spacing.SPACE_SM),
                                        ),
                                        elevation=2,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
            spacing=spacing.SPACE_XS,
            run_spacing=spacing.SPACE_MD,
            alignment=START_ALIGNMENT,
            vertical_alignment=START_ALIGNMENT,
            expand=True,
        )
        page_view.padding = spacing.SPACE_STD
        return page_view
