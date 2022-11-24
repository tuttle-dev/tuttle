import typing
from typing import Callable

from flet import Card, Column, Container, GridView, ResponsiveRow, Text, padding

from core.abstractions import LocalCache
from core.views.progress_bars import (
    horizontalProgressBar,
)
from res.utils import CONTACT_DETAILS_SCREEN_ROUTE
from core.views.spacers import mdSpace
from core.views.texts import get_headline_txt
from contacts.abstractions import ContactDestinationView
from res.colors import ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_MD, SPACE_STD
from res.strings import MY_CONTACTS, NO_CONTACTS_ADDED
from contacts.contact_intents_impl import ContactIntentImpl
from .contact_card import ContactCard


class ContactsListView(ContactDestinationView):
    def __init__(
        self,
        localCacheHandler: LocalCache,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
    ):
        super().__init__(
            intentHandler=ContactIntentImpl(cache=localCacheHandler),
            onChangeRouteCallback=onChangeRouteCallback,
        )
        self.progressBar = horizontalProgressBar
        self.noContactsComponent = Text(
            value=NO_CONTACTS_ADDED, color=ERROR_COLOR, visible=False
        )
        self.titleComponent = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt=MY_CONTACTS, size=HEADLINE_4_SIZE),
                        self.progressBar,
                        self.noContactsComponent,
                    ],
                )
            ]
        )
        self.contactsContainer = GridView(
            expand=False,
            max_extent=300,
            child_aspect_ratio=1.0,
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.contactsToDisplay = {}

    def load_all_contacts(self):
        self.contactsToDisplay = self.intentHandler.get_all_contacts()

    def display_currently_filtered_contacts(self):
        self.contactsContainer.controls.clear()
        for key in self.contactsToDisplay:
            contact = self.contactsToDisplay[key]
            contactCard = ContactCard(
                contact=contact, onClickView=self.on_view_contact_clicked
            )
            self.contactsContainer.controls.append(contactCard)

    def on_view_contact_clicked(self, contactId: str):
        self.changeRoute(CONTACT_DETAILS_SCREEN_ROUTE, contactId)

    def show_no_contacts(self):
        self.noContactsComponent.visible = True

    def did_mount(self):
        self.load_all_contacts()
        count = len(self.contactsToDisplay)
        self.progressBar.visible = False
        if count == 0:
            self.show_no_contacts()
        else:
            self.display_currently_filtered_contacts()
        self.update()

    def build(self):
        view = Card(
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(SPACE_MD),
                content=Column(
                    controls=[
                        self.titleComponent,
                        mdSpace,
                        Container(height=600, content=self.contactsContainer),
                    ]
                ),
            ),
        )
        return view
