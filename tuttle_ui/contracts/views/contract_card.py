from flet import (
    UserControl,
    Card,
    Column,
    Container,
    ElevatedButton,
    Row,
    Text,
    border_radius,
    padding,
    ResponsiveRow,
)
from res.strings import (
    START_DATE,
    END_DATE,
    CLIENT_ID_LBL,
    ID_LBL,
    VIEW_DETAILS,
    CONTRACT_BILLING_CYCLE,
    CONTRACT_TIME_UNIT,
)
from core.views import get_headline_txt
from core.constants_and_enums import (
    END_ALIGNMENT,
    CENTER_ALIGNMENT,
)
from res.colors import ERROR_COLOR, GRAY_COLOR
from res.fonts import SUBTITLE_1_SIZE, BODY_2_SIZE
from res.dimens import SPACE_STD, SPACE_XS

from typing import Callable
import typing
from contracts.contract_model import Contract


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
                        ID_LBL,
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
                        CLIENT_ID_LBL,
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
                        CONTRACT_BILLING_CYCLE,
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
                        START_DATE,
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
                        END_DATE,
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
                        text=VIEW_DETAILS,
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
