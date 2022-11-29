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
    ResponsiveRow,
)
from res.strings import EDIT_CLIENT_TOOLTIP, INVOICING_CONTACT
from core.views import get_headline_txt
from core.constants_and_enums import (
    END_ALIGNMENT,
    CENTER_ALIGNMENT,
)
from res.fonts import SUBTITLE_1_SIZE, BODY_2_SIZE
from res.dimens import SPACE_STD, SPACE_XS
from res.colors import GRAY_COLOR
from typing import Callable

from clients.client_model import Client


class ClientCard(UserControl):
    """Formats a single client info into a card ui display"""

    def __init__(self, client: Client, on_edit: Callable[[str], None]):
        super().__init__()
        self.client = client
        self.product_info_container = Column()
        self.on_edit_clicked = on_edit

    def build(self):
        if self.client.invoicing_contact:
            invoicing_contact_info = self.client.invoicing_contact.print_address()
        else:
            invoicing_contact_info = "*not specified"
        self.product_info_container.controls = [
            get_headline_txt(
                txt=self.client.title,
                size=SUBTITLE_1_SIZE,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        INVOICING_CONTACT,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Text(
                        invoicing_contact_info,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
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
                    IconButton(
                        icon=icons.EDIT_NOTE_OUTLINED,
                        tooltip=EDIT_CLIENT_TOOLTIP,
                        on_click=lambda e: self.on_edit_clicked(self.client),
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
