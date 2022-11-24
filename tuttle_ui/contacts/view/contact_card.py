from flet import (
    UserControl,
    Card,
    Column,
    Container,
    IconButton,
    icon,
    icons,
    Row,
    Text,
    border_radius,
    padding,
)
from res.strings import ID_LBL, EDIT_CONTACT_TOOLTIP, EMAIL_LBL, ADDRESS
from core.views.texts import get_headline_with_subtitle
from core.views.flet_constants import (
    END_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    CENTER_ALIGNMENT,
    START_ALIGNMENT,
)
from core.views.spacers import mdSpace, xsSpace
from res.spacing import SPACE_STD, SPACE_XS
from res.colors import GRAY_COLOR
from res.fonts import BODY_2_SIZE, CAPTION_SIZE
from typing import Callable
from contacts.contact_model import Contact

LABEL_WIDTH = 50


class ContactCard(UserControl):
    """Formats a single contact info into a card ui display"""

    def __init__(self, contact: Contact, onClickView: Callable[[str], None]):
        super().__init__()
        self.contact = contact
        self.productInfoContainer = Column(
            spacing=0,
            run_spacing=0,
        )
        self.onClickEdit = onClickView

    def build(self):
        self.productInfoContainer.controls = [
            get_headline_with_subtitle(
                title=self.contact.name,
                subtitle=self.contact.company,
                subtitleColor=GRAY_COLOR,
            ),
            mdSpace,
            Row(
                controls=[
                    Text(
                        ID_LBL.lower(),
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(self.contact.id, size=BODY_2_SIZE),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                controls=[
                    Text(
                        EMAIL_LBL.lower(),
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Text(self.contact.email, size=BODY_2_SIZE),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                controls=[
                    Text(
                        ADDRESS.lower(),
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        width=LABEL_WIDTH,
                    ),
                    Container(
                        Text(
                            self.contact.print_address(onlyAddress=True).strip(),
                            size=BODY_2_SIZE,
                        ),
                    ),
                ],
                alignment=START_ALIGNMENT,
                vertical_alignment=START_ALIGNMENT,
                spacing=SPACE_XS,
                run_spacing=SPACE_XS,
            ),
            Row(
                alignment=END_ALIGNMENT,
                vertical_alignment=END_ALIGNMENT,
                expand=True,
                controls=[
                    IconButton(
                        icon=icons.EDIT_NOTE_OUTLINED,
                        tooltip=EDIT_CONTACT_TOOLTIP,
                        on_click=lambda e: self.onClickEdit(self.contact.id),
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
