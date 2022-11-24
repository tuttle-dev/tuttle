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
from res.strings import START_DATE, END_DATE, CLIENT_ID_LBL, ID_LBL, VIEW_DETAILS
from core.views.texts import get_headline_with_subtitle, get_headline_txt
from core.views.flet_constants import END_ALIGNMENT, SPACE_BETWEEN_ALIGNMENT
from res.colors import ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_STD

from typing import Callable
import typing
from contracts.contract_model import Contract


class ContractCard(UserControl):
    """Formats a single contract info into a card ui display"""

    def __init__(self, contract: Contract, onClickView: Callable[[str], None]):
        super().__init__()
        self.contract = contract
        self.productInfoContainer = Column()
        self.onClickView = onClickView

    def build(self):
        self.productInfoContainer.controls = [
            get_headline_txt(
                txt=self.contract.title,
                size=HEADLINE_4_SIZE,
            ),
            Text(
                f"{ID_LBL} {self.contract.id}",
            ),
            Text(f"{CLIENT_ID_LBL}{self.contract.client_id}"),
            Text(f"{START_DATE} {self.contract.get_start_date_as_str()}"),
            Text(
                f"{END_DATE} {self.contract.get_end_date_as_str()}", color=ERROR_COLOR
            ),
            Row(
                alignment=SPACE_BETWEEN_ALIGNMENT,
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
