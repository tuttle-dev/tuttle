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
from res.strings import ID_LBL, VIEW_DETAILS, EMAIL_LBL, COMPANY_LBL
from core.views.texts import get_headline_txt
from core.views.flet_constants import END_ALIGNMENT, SPACE_BETWEEN_ALIGNMENT
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_STD

from typing import Callable
import typing
from contacts.contact_model import Contact


class ContactCard(UserControl):
    """Formats a single contact info into a card ui display"""

    def __init__(self, contact: Contact, onClickView: Callable[[str], None]):
        super().__init__()
        self.contact = contact
        self.productInfoContainer = Column()
        self.onClickView = onClickView

    def build(self):
        self.productInfoContainer.controls = [
            get_headline_txt(
                txt=self.contact.name,
                size=HEADLINE_4_SIZE,
            ),
            Text(
                f"{ID_LBL} {self.contact.id}",
            ),
            Text(f"{EMAIL_LBL} {self.contact.email}"),
            Text(f"{COMPANY_LBL} {self.contact.company}"),
            Row(
                alignment=SPACE_BETWEEN_ALIGNMENT,
                vertical_alignment=END_ALIGNMENT,
                expand=True,
                controls=[
                    ElevatedButton(
                        text=VIEW_DETAILS,
                        on_click=lambda e: self.onClickView(self.contact.id),
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
