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
    ResponsiveRow,
    ListTile,
    Icon,
)
from res.strings import ID_LBL, EDIT_CONTACT_TOOLTIP, EMAIL_LBL, ADDRESS
from core.views import get_headline_with_subtitle
from core.constants_and_enums import (
    END_ALIGNMENT,
    CENTER_ALIGNMENT,
    START_ALIGNMENT,
)
from core.views import mdSpace
from res.dimens import SPACE_STD, SPACE_XS
from res.colors import GRAY_COLOR
from res.fonts import BODY_2_SIZE
from typing import Callable
from contacts.contact_model import Contact


class ContactCard(UserControl):
    """Formats a single contact info into a card ui display"""

    def __init__(self, contact: Contact, on_edit_clicked: Callable[[str], None]):
        super().__init__()
        self.contact = contact
        self.product_info_container = Column(
            spacing=0,
            run_spacing=0,
        )
        self.on_edit_clicked = on_edit_clicked

    def build(self):
        self.product_info_container.controls = [
            ListTile(
                leading=Icon(icons.CONTACT_MAIL),
                title=Text(self.contact.name),
                subtitle=Text(self.contact.company, color=GRAY_COLOR),
                trailing=IconButton(
                    icon=icons.EDIT_NOTE_OUTLINED,
                    tooltip=EDIT_CONTACT_TOOLTIP,
                    on_click=lambda e: self.on_edit_clicked(self.contact),
                ),
            ),
            # get_headline_with_subtitle(
            #     title=self.contact.name,
            #     subtitle=self.contact.company,
            #     subtitleColor=GRAY_COLOR,
            # ),
            mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        EMAIL_LBL.lower(),
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Text(
                        self.contact.email,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        ADDRESS.lower(),
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        Text(
                            self.contact.print_address(onlyAddress=True).strip(),
                            size=BODY_2_SIZE,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=START_ALIGNMENT,
                vertical_alignment=START_ALIGNMENT,
                spacing=SPACE_XS,
                run_spacing=0,
            ),
            # Row(
            #     alignment=END_ALIGNMENT,
            #     vertical_alignment=END_ALIGNMENT,
            #     expand=True,
            #     controls=[
            #         IconButton(
            #             icon=icons.EDIT_NOTE_OUTLINED,
            #             tooltip=EDIT_CONTACT_TOOLTIP,
            #             on_click=lambda e: self.on_edit_clicked(self.contact),
            #         ),
            #     ],
            # ),
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
