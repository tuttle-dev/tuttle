import typing
from typing import Callable, Optional

from flet import (
    AlertDialog,
    Card,
    Column,
    Container,
    GridView,
    IconButton,
    ResponsiveRow,
    Row,
    Text,
    UserControl,
    border_radius,
    Icon,
    icons,
    padding,
    ListTile,
)

from contacts.model import Contact, get_empty_contact
from contacts.intent import ContactsIntent
from core.abstractions import DialogHandler, TuttleView
from core.utils import (
    ALWAYS_SCROLL,
    AUTO_SCROLL,
    CENTER_ALIGNMENT,
    END_ALIGNMENT,
    START_ALIGNMENT,
    AlertDialogControls,
)
from core.models import IntentResult
from core.views import (
    CENTER_ALIGNMENT,
    get_headline_txt,
    get_headline_with_subtitle,
    get_primary_btn,
    get_std_txt_field,
    horizontal_progress,
    mdSpace,
    xsSpace,
)
from res.colors import ERROR_COLOR, GRAY_COLOR
from res.dimens import MIN_WINDOW_WIDTH, SPACE_MD, SPACE_STD, SPACE_XS
from res.fonts import BODY_2_SIZE, HEADLINE_4_SIZE

from res.res_utils import ADD_CONTACT_INTENT

from tuttle.model import (
    Address,
)


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
                    tooltip="Edit Contact",
                    on_click=lambda e: self.on_edit_clicked(self.contact),
                ),
            ),
            mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "email",
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
                        "address",
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


class ContactEditorPopUp(DialogHandler):
    """Pop up used for editing a contact"""

    def __init__(
        self,
        dialog_controller: Callable[[any, AlertDialogControls], None],
        on_submit: Callable,
        contact: Optional[Contact] = None,
    ):
        self.dialog_height = 550
        self.dialog_width = int(MIN_WINDOW_WIDTH * 0.8)
        self.half_of_dialog_width = int(MIN_WINDOW_WIDTH * 0.35)
        self.contact = contact
        if not self.contact:
            # user is creating a new contact
            self.contact = get_empty_contact()
        self.address = self.contact.address

        title = "Edit contact" if contact is not None else "Add contact"

        dialog = AlertDialog(
            content=Container(
                height=self.dialog_height,
                content=Column(
                    scroll=AUTO_SCROLL,
                    controls=[
                        get_headline_txt(txt=title, size=HEADLINE_4_SIZE),
                        xsSpace,
                        get_std_txt_field(
                            on_change=self.on_fname_changed,
                            lbl="First Name",
                            hint=self.contact.first_name,
                            initial_value=self.contact.first_name,
                        ),
                        get_std_txt_field(
                            on_change=self.on_lname_changed,
                            lbl="Last Name",
                            hint=self.contact.last_name,
                            initial_value=self.contact.last_name,
                        ),
                        get_std_txt_field(
                            on_change=self.on_company_changed,
                            lbl="Company",
                            hint=self.contact.company,
                            initial_value=self.contact.company,
                        ),
                        get_std_txt_field(
                            on_change=self.on_email_changed,
                            lbl="Email",
                            hint=self.contact.email,
                            initial_value=self.contact.email,
                        ),
                        Row(
                            vertical_alignment=CENTER_ALIGNMENT,
                            controls=[
                                get_std_txt_field(
                                    on_change=self.on_street_changed,
                                    lbl="Street",
                                    hint=self.contact.address.street,
                                    initial_value=self.contact.address.street,
                                    width=self.half_of_dialog_width,
                                ),
                                get_std_txt_field(
                                    on_change=self.on_street_num_changed,
                                    lbl="Street No.",
                                    hint=self.contact.address.number,
                                    initial_value=self.contact.address.number,
                                    width=self.half_of_dialog_width,
                                ),
                            ],
                        ),
                        Row(
                            vertical_alignment=CENTER_ALIGNMENT,
                            controls=[
                                get_std_txt_field(
                                    on_change=self.on_postal_code_changed,
                                    lbl="Postal code",
                                    hint=self.contact.address.postal_code,
                                    initial_value=self.contact.address.postal_code,
                                    width=self.half_of_dialog_width,
                                ),
                                get_std_txt_field(
                                    on_change=self.on_city_changed,
                                    lbl="City",
                                    hint=self.contact.address.city,
                                    initial_value=self.contact.address.city,
                                    width=self.half_of_dialog_width,
                                ),
                            ],
                        ),
                        get_std_txt_field(
                            on_change=self.on_country_changed,
                            lbl="Country",
                            hint=self.contact.address.country,
                            initial_value=self.contact.address.country,
                        ),
                        xsSpace,
                    ],
                ),
                width=self.dialog_width,
            ),
            actions=[
                get_primary_btn(label="Done", on_click=self.on_submit_btn_clicked),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)

        self.fname = ""
        self.lname = ""
        self.company = ""
        self.email = ""
        self.street = ""
        self.street_num = ""
        self.postal_code = ""
        self.city = ""
        self.country = ""
        self.on_submit = on_submit

    def on_fname_changed(self, e):
        self.fname = e.control.value

    def on_lname_changed(self, e):
        self.lname = e.control.value

    def on_company_changed(self, e):
        self.company = e.control.value

    def on_email_changed(self, e):
        self.email = e.control.value

    def on_street_changed(self, e):
        self.street = e.control.value

    def on_street_num_changed(self, e):
        self.street_num = e.control.value

    def on_postal_code_changed(self, e):
        self.postal_code = e.control.value

    def on_city_changed(self, e):
        self.city = e.control.value

    def on_country_changed(self, e):
        self.country = e.control.value

    def on_submit_btn_clicked(self, e):

        self.contact.first_name = (
            self.fname.strip() if self.fname.strip() else self.contact.first_name
        )
        self.contact.last_name = (
            self.lname.strip() if self.lname.strip() else self.contact.last_name
        )
        self.contact.company = (
            self.company.strip() if self.company.strip() else self.contact.company
        )
        self.contact.email = (
            self.email.strip() if self.email.strip() else self.contact.email
        )
        self.address.street = (
            self.street.strip() if self.street.strip() else self.contact.address.street
        )

        self.address.number = (
            self.street_num.strip()
            if self.street_num.strip()
            else self.contact.address.number
        )
        self.address.postal_code = (
            self.postal_code.strip()
            if self.postal_code.strip()
            else self.contact.address.postal_code
        )
        self.address.city = (
            self.city.strip() if self.city.strip() else self.contact.address.city
        )
        self.address.country = (
            self.country.strip()
            if self.country.strip()
            else self.contact.address.country
        )
        self.contact.address = self.address
        self.close_dialog()
        self.on_submit(self.contact)


class ContactsListView(TuttleView, UserControl):
    def __init__(self, navigate_to_route, show_snack, dialog_controller, local_storage):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = ContactsIntent(local_storage=local_storage)
        self.loading_indicator = horizontal_progress
        self.no_contacts_control = Text(
            value="You have not added any contacts yet",
            color=ERROR_COLOR,
            visible=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt="My Contacts", size=HEADLINE_4_SIZE),
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
            if self.editor:
                self.editor.close_dialog()
            self.editor = ContactEditorPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=self.on_new_contact_added,
            )
            self.editor.open_dialog()
        return

    def on_new_contact_added(self, contact):
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
            self.show_snack("A new contact has been added", False)
        self.loading_indicator.visible = False
        if self.mounted:
            self.update()

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
            "The contact's info has been updated"
            if result.was_intent_successful
            else "Failed to update the contact"
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
            self.show_snack("Loading contacts failed.")
            self.loading_indicator.visible = False
            if self.mounted:
                self.update()

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
