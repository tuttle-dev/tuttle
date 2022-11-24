from flet import (
    UserControl,
    Card,
    Column,
    Container,
    IconButton,
    icons,
    Row,
    Text,
    border_radius,
    padding,
)
from res.strings import (
    ID_LBL,
    EDIT_CLIENT_TOOLTIP,
    INVOICING_CONTACT_ID,
)
from core.views.texts import get_headline_txt
from core.views.flet_constants import (
    END_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    CENTER_ALIGNMENT,
)
from res.fonts import SUBTITLE_1_SIZE, BODY_2_SIZE
from res.spacing import SPACE_STD, SPACE_XS
from res.colors import GRAY_COLOR
from typing import Callable
import typing
from clients.client_model import Client

LABEL_WIDTH = 80


class ClientCard(UserControl):
    """Formats a single client info into a card ui display"""

    def __init__(self, client: Client, onClickView: Callable[[str], None]):
        super().__init__()
        self.client = client
        self.productInfoContainer = Column()
        self.onClickEdit = onClickView

    def build(self):
        self.productInfoContainer.controls = [
            get_headline_txt(
                txt=self.client.title,
                size=SUBTITLE_1_SIZE,
            ),
            Row(
                controls=[
                    Text(
                        ID_LBL,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(self.client.id, size=BODY_2_SIZE),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                controls=[
                    Text(
                        INVOICING_CONTACT_ID.lower(),
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(self.client.invoicing_contact_id, size=BODY_2_SIZE),
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
                    IconButton(
                        icon=icons.EDIT_NOTE_OUTLINED,
                        tooltip=EDIT_CLIENT_TOOLTIP,
                        on_click=lambda e: self.onClickEdit(self.client.id),
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
