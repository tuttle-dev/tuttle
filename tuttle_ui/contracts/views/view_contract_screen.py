import typing
from typing import Callable, Optional

from flet import (
    Card,
    Column,
    Container,
    Icon,
    IconButton,
    Row,
    Text,
    TextButton,
    UserControl,
    icons,
    padding,
    ResponsiveRow,
)
from core.models import IntentResult
from contracts.contract_model import Contract
from contracts.intent_impl import ContractsIntentImpl
from core.abstractions import ClientStorage, TuttleView
from core.constants_and_enums import (
    CENTER_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_JUSTIFY,
    AlertDialogControls,
)
from core.views import horizontalProgressBar, mdSpace
from res import colors, fonts, dimens
from res.dimens import MIN_WINDOW_WIDTH
from res.strings import (
    CLIENT_LBL,
    CONTRACT_BILLING_CYCLE,
    CONTRACT_CURRENCY,
    CONTRACT_LBL,
    CONTRACT_RATE,
    CONTRACT_SIGNATURE_DATE,
    CONTRACT_STATUS_LBL,
    CONTRACT_TERM_OF_PAYMENT,
    CONTRACT_TIME_UNIT,
    CONTRACT_UNITS_PER_WORKDAY,
    CONTRACT_VAT_RATE,
    CONTRACT_VOLUME,
    DELETE_CONTRACT,
    EDIT_CONTRACT,
    END_DATE,
    MARK_AS_COMPLETE,
    START_DATE,
    VIEW_CLIENT_HINT,
    VIEW_CLIENT_LBL,
)

LABEL_WIDTH = 80


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
        self.intent_handler = ContractsIntentImpl(local_storage=local_storage)
        self.contract_id = contract_id
        self.loading_indicator = horizontalProgressBar
        self.contract: Optional[Contract] = None

    def display_contract_data(self):
        self.contract_title_control.value = self.contract.title
        self.client_control.value = self.contract.client.title
        self.contract_title_control.value = self.contract.title
        self.start_date_control.value = self.contract.start_date
        self.end_date_control.value = self.contract.end_date
        self.status_control.value = (
            f"{CONTRACT_STATUS_LBL} {self.contract.get_status()}"
        )
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
            tooltip=EDIT_CONTRACT,
            on_click=self.on_edit_clicked,
        )
        self.mark_as_complete_btn = IconButton(
            icon=icons.CHECK_CIRCLE_OUTLINE,
            icon_color=colors.PRIMARY_COLOR,
            tooltip=MARK_AS_COMPLETE,
            on_click=self.on_mark_as_complete_clicked,
        )
        self.delete_contract_btn = IconButton(
            icon=icons.DELETE_OUTLINE_ROUNDED,
            icon_color=colors.ERROR_COLOR,
            tooltip=DELETE_CONTRACT,
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
                                VIEW_CLIENT_LBL,
                                tooltip=VIEW_CLIENT_HINT,
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
                                                        CONTRACT_LBL,
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
                                                CONTRACT_LBL,
                                                self.contract_title_control,
                                            ),
                                            self.get_body_element(
                                                CLIENT_LBL, self.client_control
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            mdSpace,
                            self.get_body_element(
                                CONTRACT_BILLING_CYCLE, self.billing_cycle_control
                            ),
                            self.get_body_element(CONTRACT_RATE, self.rate_control),
                            self.get_body_element(
                                CONTRACT_CURRENCY, self.currency_control
                            ),
                            self.get_body_element(
                                CONTRACT_VAT_RATE, self.vat_rate_control
                            ),
                            self.get_body_element(
                                CONTRACT_TIME_UNIT, self.unit_control
                            ),
                            self.get_body_element(
                                CONTRACT_UNITS_PER_WORKDAY,
                                self.units_per_workday_control,
                            ),
                            self.get_body_element(CONTRACT_VOLUME, self.volume_control),
                            self.get_body_element(
                                CONTRACT_TERM_OF_PAYMENT, self.term_of_payment_control
                            ),
                            self.get_body_element(
                                CONTRACT_SIGNATURE_DATE, self.signature_date_control
                            ),
                            self.get_body_element(START_DATE, self.start_date_control),
                            self.get_body_element(END_DATE, self.end_date_control),
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
