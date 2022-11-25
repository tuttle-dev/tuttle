import typing
from typing import Callable, Optional

from flet import Card, Column, Container, GridView, ResponsiveRow, Text, padding

from res.utils import ADD_CONTACT_INTENT
from core.abstractions import LocalCache
from core.views.progress_bars import (
    horizontalProgressBar,
)
from core.views.alert_dialog_controls import AlertDialogControls
from core.models import Address
from contacts.contact_model import Contact
from .contact_editor import EditContactPopUp
from core.views.spacers import mdSpace
from core.views.texts import get_headline_txt
from contacts.abstractions import ContactDestinationView
from res.colors import ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_MD, SPACE_STD
from res.strings import (
    MY_CONTACTS,
    NO_CONTACTS_ADDED,
    UPDATING_ADDRESS_FAILED,
    UPDATING_CONTACT_FAILED,
    UPDATING_CONTACT_SUCCESS,
    NEW_CONTACT_ADDED_SUCCESS,
)
from contacts.contact_intents_impl import ContactIntentImpl
from .contact_card import ContactCard


class ContactsListView(ContactDestinationView):
    def __init__(
        self,
        localCacheHandler: LocalCache,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
        pageDialogController: Callable[[any, AlertDialogControls], None],
        showSnackCallback=Callable,
    ):
        super().__init__(
            intentHandler=ContactIntentImpl(cache=localCacheHandler),
            onChangeRouteCallback=onChangeRouteCallback,
            pageDialogController=pageDialogController,
        )
        self.showSnack = showSnackCallback
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
        self.editor = None

    def parent_intent_listener(self, intent: str, data: any):
        if intent == ADD_CONTACT_INTENT:
            """New contact was clicked"""
            contact: Contact = data
            self.progressBar.visible = True
            self.update()
            result = self.intentHandler.create_contact_and_address(contact=contact)
            if not result.wasIntentSuccessful:
                self.showSnack(result.errorMsg, True)

            else:
                contact = result.data
                self.contactsToDisplay[contact.id] = contact
                self.refresh_list()
                self.showSnack(NEW_CONTACT_ADDED_SUCCESS, False)
            self.progressBar.visible = False
            self.update()
        return

    def load_all_contacts(self):
        self.contactsToDisplay = self.intentHandler.get_all_contacts()

    def refresh_list(self):
        self.contactsContainer.controls.clear()
        for key in self.contactsToDisplay:
            contact = self.contactsToDisplay[key]
            contactCard = ContactCard(
                contact=contact,
                onClickView=self.on_view_contact_clicked,
            )
            self.contactsContainer.controls.append(contactCard)

    def on_view_contact_clicked(self, contact: Contact):
        # pop up
        if self.editor:
            self.editor.close_dialog()
        self.editor = EditContactPopUp(
            dialogController=self.pageDialogController,
            contact=contact,
            onUpdate=self.on_update_contact,
        )
        self.editor.open_dialog()

    def on_update_contact(
        self,
        contact_id: str,
        address_id: Optional[int],
        fname: str,
        lname: str,
        company: str,
        email: str,
        street: str,
        street_num: str,
        postal_code: str,
        city: str,
        country: str,
    ):
        self.progressBar.visible = True
        self.update()
        result = self.intentHandler.create_or_update_address(
            address_id=address_id,
            street=street,
            number=street_num,
            postal_code=postal_code,
            city=city,
            country=country,
        )
        if not result.wasIntentSuccessful:
            """an error occurred"""
            self.showSnack(UPDATING_ADDRESS_FAILED, True)
            self.progressBar.visible = False
            self.update()
            return

        newAddress: Address = result.data
        result = self.intentHandler.create_or_update_contact(
            contact_id=contact_id,
            company=company,
            first_name=fname,
            last_name=lname,
            email=email,
            address=newAddress,
        )
        msg = (
            UPDATING_CONTACT_SUCCESS
            if result.wasIntentSuccessful
            else UPDATING_CONTACT_FAILED
        )
        isError = False if result.wasIntentSuccessful else True
        self.showSnack(msg, isError)
        self.progressBar.visible = False
        if not isError:
            updatedContact: Contact = result.data
            self.contactsToDisplay[updatedContact.id] = updatedContact
            self.refresh_list()
        self.update()

    def show_no_contacts(self):
        self.noContactsComponent.visible = True

    def did_mount(self):
        self.load_all_contacts()
        count = len(self.contactsToDisplay)
        self.progressBar.visible = False
        if count == 0:
            self.show_no_contacts()
        else:
            self.refresh_list()
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

    def will_unmount(self):
        try:
            if self.editor:
                self.editor.dimiss_open_dialogs()
        except Exception as e:
            print(e)
