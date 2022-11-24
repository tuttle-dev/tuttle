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
from core.views.texts import get_headline_txt
from core.views.flet_constants import (
    END_ALIGNMENT,
    CENTER_ALIGNMENT,
)
from res.colors import ERROR_COLOR, GRAY_COLOR
from res.fonts import SUBTITLE_1_SIZE, BODY_2_SIZE
from res.spacing import SPACE_STD, SPACE_XS

from typing import Callable
import typing
from contracts.contract_model import Contract

LABEL_WIDTH = 70


class ContractCard(UserControl):
    """Formats a single contract info into a card ui display"""

    def __init__(self, contract: Contract, onClickView: Callable[[str], None]):
        super().__init__()
        self.contract = contract
        self.productInfoContainer = Column()
        self.onClickView = onClickView

    def build(self):
        self.productInfoContainer.controls = [
            get_headline_txt(txt=self.contract.title, size=SUBTITLE_1_SIZE),
            Row(
                controls=[
                    Text(
                        ID_LBL,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(self.contract.id, size=BODY_2_SIZE),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                controls=[
                    Text(
                        CLIENT_ID_LBL,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(self.contract.client_id, size=BODY_2_SIZE),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                controls=[
                    Text(
                        CONTRACT_BILLING_CYCLE,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(self.contract.billing_cycle, size=BODY_2_SIZE),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                controls=[
                    Text(
                        START_DATE,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(self.contract.get_start_date_as_str(), size=BODY_2_SIZE),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                controls=[
                    Text(
                        END_DATE,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(
                        self.contract.get_end_date_as_str(),
                        size=BODY_2_SIZE,
                        color=ERROR_COLOR,
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
                        on_click=lambda e: self.onClickView(self.contract.id),
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
                content=self.productInfoContainer,
            ),
        )
        return card
