import typing
from typing import Callable, Optional

from flet import (
    Card,
    Column,
    Container,
    GridView,
    ResponsiveRow,
    Text,
    UserControl,
    padding,
)
from core.constants_and_enums import ALWAYS_SCROLL
from contacts.contact_model import Contact
from contacts.intent_impl import ContactsIntentImpl
from core.abstractions import TuttleView
from core.models import IntentResult
from core.views import get_headline_txt, horizontal_progress, mdSpace
from res.colors import ERROR_COLOR
from res.dimens import SPACE_MD, SPACE_STD
from res.fonts import HEADLINE_4_SIZE
from res.strings import (
    MY_CONTACTS,
    NEW_CONTACT_ADDED_SUCCESS,
    NO_CONTACTS_ADDED,
    UPDATING_CONTACT_SUCCESS,
    UPDATING_CONTACT_FAILED,
)
from res.utils import ADD_CONTACT_INTENT

from .contact_card import ContactCard
from .contact_editor import ContactEditorPopUp


class ContactsListView(TuttleView, UserControl):
    def __init__(self, navigate_to_route, show_snack, dialog_controller, local_storage):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = ContactsIntentImpl(local_storage=local_storage)
        self.loading_indicator = horizontal_progress
        self.no_contacts_control = Text(
            value=NO_CONTACTS_ADDED, color=ERROR_COLOR, visible=False
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt=MY_CONTACTS, size=HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.no_contacts_control,
                    ],
                )
            ]
        )
        self.contacts_container = GridView(
            expand=False,
            max_extent=540,
            child_aspect_ratio=1.0,
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.contacts_to_display = {}
        self.editor = None

    def parent_intent_listener(self, intent: str, data: any):
        if intent == ADD_CONTACT_INTENT:
            """New contact was clicked"""
            contact: Contact = data
            self.loading_indicator.visible = True
            if self.mounted:
                self.update()
            result: IntentResult = self.intent_handler.save_contact(contact)
            if not result.was_intent_successful:
                self.show_snack(result.error_msg, True)
            else:
                contact = result.data
                self.contacts_to_display[contact.id] = contact
                self.refresh_list()
                self.show_snack(NEW_CONTACT_ADDED_SUCCESS, False)
            self.loading_indicator.visible = False
            if self.mounted:
                self.update()
        return

    def load_all_contacts(self):
        self.contacts_to_display = self.intent_handler.get_all_contacts_as_map()

    def refresh_list(self):
        self.contacts_container.controls.clear()
        for key in self.contacts_to_display:
            contact = self.contacts_to_display[key]
            contactCard = ContactCard(
                contact=contact,
                on_edit_clicked=self.on_edit_contact_clicked,
            )
            self.contacts_container.controls.append(contactCard)

    def on_edit_contact_clicked(self, contact: Contact):
        if self.editor:
            self.editor.close_dialog()
        self.editor = ContactEditorPopUp(
            dialog_controller=self.dialog_controller,
            contact=contact,
            on_submit=self.on_update_contact,
        )

        self.editor.open_dialog()

    def on_update_contact(self, contact):
        self.loading_indicator.visible = True
        if self.mounted:
            self.update()
        result = self.intent_handler.save_contact(contact)
        msg = (
            UPDATING_CONTACT_SUCCESS
            if result.was_intent_successful
            else UPDATING_CONTACT_FAILED
        )
        isError = False if result.was_intent_successful else True
        self.show_snack(msg, isError)
        self.loading_indicator.visible = False
        if not isError:
            updatedContact: Contact = result.data
            self.contacts_to_display[updatedContact.id] = updatedContact
            self.refresh_list()
        if self.mounted:
            self.update()

    def show_no_contacts(self):
        self.no_contacts_control.visible = True

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.load_all_contacts()
            count = len(self.contacts_to_display)
            self.loading_indicator.visible = False
            if count == 0:
                self.show_no_contacts()
            else:
                self.refresh_list()
            if self.mounted:
                self.update()
        except Exception as e:
            print(f"exception raised @contacts.did_mount {e}")

    def build(self):
        view = Column(
            controls=[
                self.title_control,
                mdSpace,
                Container(self.contacts_container, expand=True),
            ]
        )
        return view

    def will_unmount(self):
        try:
            self.mounted = False
            if self.editor:
                self.editor.dimiss_open_dialogs()
        except Exception as e:
            print(e)
