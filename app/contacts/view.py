from typing import Callable, Optional

from flet import (
    AlertDialog,
    Card,
    Column,
    Container,
    GridView,
    Icon,
    ListTile,
    ResponsiveRow,
    Row,
    UserControl,
    border_radius,
    padding,
)

from contacts.intent import ContactsIntent
from core import utils, views
from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from core.intent_result import IntentResult
from res import colors, dimens, fonts, res_utils

from tuttle.model import Address, Contact


class ContactCard(UserControl):
    """Formats a single contact info into a card ui display"""

    def __init__(
        self,
        contact: Contact,
        on_edit_clicked,
        on_deleted_clicked,
    ):
        super().__init__()
        self.contact = contact
        self.contact_info_container = Column(
            spacing=0,
            run_spacing=0,
        )
        self.on_edit_clicked = on_edit_clicked
        self.on_deleted_clicked = on_deleted_clicked

    def build(self):
        """Builds the contact card"""
        self.contact_info_container.controls = [
            ListTile(
                leading=Icon(
                    utils.TuttleComponentIcons.contact_icon,
                    size=dimens.ICON_SIZE,
                ),
                title=views.get_body_txt(utils.truncate_str(self.contact.name)),
                subtitle=views.get_body_txt(
                    utils.truncate_str(self.contact.company), color=colors.GRAY_COLOR
                ),
                trailing=views.context_pop_up_menu(
                    on_click_edit=lambda e: self.on_edit_clicked(self.contact),
                    on_click_delete=lambda e: self.on_deleted_clicked(self.contact),
                ),
            ),
            views.mdSpace,
            ResponsiveRow(
                controls=[
                    views.get_body_txt(
                        txt="email",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    views.get_body_txt(
                        txt=self.contact.email,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                ],
                spacing=dimens.SPACE_XS,
                run_spacing=0,
                vertical_alignment=utils.CENTER_ALIGNMENT,
            ),
            views.mdSpace,
            ResponsiveRow(
                controls=[
                    views.get_body_txt(
                        txt="address",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        views.get_body_txt(
                            txt=self.contact.print_address(address_only=True).strip(),
                            size=fonts.BODY_2_SIZE,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=utils.START_ALIGNMENT,
                vertical_alignment=utils.START_ALIGNMENT,
                spacing=dimens.SPACE_XS,
                run_spacing=0,
            ),
        ]
        return Card(
            elevation=2,
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(dimens.SPACE_STD),
                border_radius=border_radius.all(12),
                content=self.contact_info_container,
            ),
        )


class ContactEditorPopUp(DialogHandler):
    """Pop up used for editing a contact"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_submit: Callable,
        contact: Optional[Contact] = None,
    ):
        # dimensions of the pop up
        pop_up_height = 550
        pop_up_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)
        width_spanning_half_of_container = int(dimens.MIN_WINDOW_WIDTH * 0.35)
        self.contact = contact
        if not self.contact:
            # user is creating a new contact
            self.contact = Contact()
            self.contact.address = Address()
        self.address = self.contact.address

        title = "Edit contact" if contact is not None else "Add contact"

        dialog = AlertDialog(
            content=Container(
                height=pop_up_height,
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.get_heading(title=title, size=fonts.HEADLINE_4_SIZE),
                        views.xsSpace,
                        views.get_std_txt_field(
                            on_change=self.on_fname_changed,
                            label="First Name",
                            hint=self.contact.first_name,
                            initial_value=self.contact.first_name,
                        ),
                        views.get_std_txt_field(
                            on_change=self.on_lname_changed,
                            label="Last Name",
                            hint=self.contact.last_name,
                            initial_value=self.contact.last_name,
                        ),
                        views.get_std_txt_field(
                            on_change=self.on_company_changed,
                            label="Company",
                            hint=self.contact.company,
                            initial_value=self.contact.company,
                        ),
                        views.get_std_txt_field(
                            on_change=self.on_email_changed,
                            label="Email",
                            hint=self.contact.email,
                            initial_value=self.contact.email,
                        ),
                        Row(
                            vertical_alignment=utils.CENTER_ALIGNMENT,
                            controls=[
                                views.get_std_txt_field(
                                    on_change=self.on_street_changed,
                                    label="Street",
                                    hint=self.contact.address.street,
                                    initial_value=self.contact.address.street,
                                    width=width_spanning_half_of_container,
                                ),
                                views.get_std_txt_field(
                                    on_change=self.on_street_num_changed,
                                    label="Street No.",
                                    hint=self.contact.address.number,
                                    initial_value=self.contact.address.number,
                                    width=width_spanning_half_of_container,
                                ),
                            ],
                        ),
                        Row(
                            vertical_alignment=utils.CENTER_ALIGNMENT,
                            controls=[
                                views.get_std_txt_field(
                                    on_change=self.on_postal_code_changed,
                                    label="Postal code",
                                    hint=self.contact.address.postal_code,
                                    initial_value=self.contact.address.postal_code,
                                    width=width_spanning_half_of_container,
                                ),
                                views.get_std_txt_field(
                                    on_change=self.on_city_changed,
                                    label="City",
                                    hint=self.contact.address.city,
                                    initial_value=self.contact.address.city,
                                    width=width_spanning_half_of_container,
                                ),
                            ],
                        ),
                        views.get_std_txt_field(
                            on_change=self.on_country_changed,
                            label="Country",
                            hint=self.contact.address.country,
                            initial_value=self.contact.address.country,
                        ),
                        views.xsSpace,
                    ],
                ),
                width=pop_up_width,
            ),
            actions=[
                views.get_primary_btn(
                    label="Done", on_click=self.on_submit_btn_clicked
                ),
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
        self.on_submit_callback = on_submit

    def on_fname_changed(self, e):
        """Called when the first name field is changed"""
        self.fname = e.control.value

    def on_lname_changed(self, e):
        """Called when the last name field is changed"""
        self.lname = e.control.value

    def on_company_changed(self, e):
        """Called when the company field is changed"""
        self.company = e.control.value

    def on_email_changed(self, e):
        """Called when the email field is changed"""
        self.email = e.control.value

    def on_street_changed(self, e):
        """Called when the street field is changed"""
        self.street = e.control.value

    def on_street_num_changed(self, e):
        """Called when the street number field is changed"""
        self.street_num = e.control.value

    def on_postal_code_changed(self, e):
        """Called when the postal code field is changed"""
        self.postal_code = e.control.value

    def on_city_changed(self, e):
        """Called when the city field is changed"""
        self.city = e.control.value

    def on_country_changed(self, e):
        """Called when the country field is changed"""
        self.country = e.control.value

    def on_submit_btn_clicked(self, e):
        """Called when the submit button is clicked"""
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
        self.on_submit_callback(self.contact)


class ContactsListView(TuttleView, UserControl):
    """The view for the contacts list page"""

    def __init__(self, params: TuttleViewParams):
        super().__init__(params)
        self.intent = ContactsIntent()
        self.loading_indicator = views.horizontal_progress
        self.no_contacts_control = views.get_body_txt(
            txt="You have not added any contacts yet",
            color=colors.ERROR_COLOR,
            show=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.get_heading(
                            title="My Contacts", size=fonts.HEADLINE_4_SIZE
                        ),
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
            spacing=dimens.SPACE_STD,
            run_spacing=dimens.SPACE_MD,
        )
        self.contacts_to_display = {}
        self.editor = None

    def parent_intent_listener(self, intent: str, data: any):
        """Called when the parent view passes an intent"""
        if intent == res_utils.ADD_CONTACT_INTENT:
            # Open the contact editor
            if self.editor:
                self.editor.close_dialog()
            self.editor = ContactEditorPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=self.on_new_contact_added,
            )
            self.editor.open_dialog()
        elif intent == res_utils.RELOAD_INTENT:
            # Reload the contacts
            self.reload_all_data()

    def on_new_contact_added(self, contact):
        """Called when a new contact is added"""
        self.loading_indicator.visible = True
        self.update_self()
        result: IntentResult = self.intent.save_contact(contact)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            contact = result.data
            self.contacts_to_display[contact.id] = contact
            self.refresh_list()
            self.show_snack("A new contact has been added", False)
        self.loading_indicator.visible = False
        self.update_self()

    def load_all_contacts(self):

        self.contacts_to_display = self.intent.get_all_contacts_as_map()

    def refresh_list(self):
        """Refreshes the displayed list of contacts"""
        self.contacts_container.controls.clear()
        for key in self.contacts_to_display:
            contact = self.contacts_to_display[key]
            contactCard = ContactCard(
                contact=contact,
                on_edit_clicked=self.on_edit_contact_clicked,
                on_deleted_clicked=self.on_delete_contact_clicked,
            )
            self.contacts_container.controls.append(contactCard)

    def on_edit_contact_clicked(self, contact: Contact):
        """Called when the edit button is clicked"""
        if self.editor:
            self.editor.close_dialog()
        self.editor = ContactEditorPopUp(
            dialog_controller=self.dialog_controller,
            contact=contact,
            on_submit=self.on_update_contact,
        )

        self.editor.open_dialog()

    def on_delete_contact_clicked(self, contact: Contact):
        """Called when the delete button is clicked"""
        if self.editor:
            self.editor.close_dialog()
        # Open the confirmation dialog
        self.editor = views.ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description=f"Are you sure you wish to delete this contact?\n{contact.first_name} {contact.last_name}",
            on_proceed=self.on_delete_confirmed,
            proceed_button_label="Yes! Delete",
            data_on_confirmed=contact.id,
        )

        self.editor.open_dialog()

    def on_delete_confirmed(self, contact_id):
        """Called when the user confirms the deletion of a contact"""
        self.loading_indicator.visible = True
        self.update_self()
        result = self.intent.delete_contact_by_id(contact_id)
        is_error = False if result.was_intent_successful else True
        msg = "Contact deleted!" if not is_error else result.error_msg
        self.show_snack(msg, is_error)
        self.loading_indicator.visible = False
        if not is_error and contact_id in self.contacts_to_display:
            del self.contacts_to_display[contact_id]
            self.refresh_list()
        self.update_self()

    def on_update_contact(self, contact):
        """Called when a contact is updated"""
        self.loading_indicator.visible = True
        self.update_self()
        result = self.intent.save_contact(contact)
        is_error = False if result.was_intent_successful else True
        msg = (
            "The contact's info has been updated" if not is_error else result.error_msg
        )

        self.show_snack(msg, is_error)
        self.loading_indicator.visible = False
        if not is_error:
            updated_contact: Contact = result.data
            self.contacts_to_display[updated_contact.id] = updated_contact
            self.refresh_list()
        self.update_self()

    def did_mount(self):
        """Called when the view is mounted"""
        self.reload_all_data()

    def reload_all_data(self):
        """Reloads all the data when view is mounted or parent view passes a reload intent"""
        self.mounted = True
        self.loading_indicator.visible = True
        self.load_all_contacts()
        count = len(self.contacts_to_display)
        self.loading_indicator.visible = False
        if count == 0:
            self.no_contacts_control.visible = True
            self.contacts_container.controls.clear()
        else:
            self.no_contacts_control.visible = False
            self.refresh_list()
        self.update_self()

    def build(self):
        """Builds the view"""
        return Column(
            controls=[
                self.title_control,
                views.mdSpace,
                Container(self.contacts_container, expand=True),
            ]
        )

    def will_unmount(self):
        """Called when the view is unmounted"""
        self.mounted = False
        if self.editor:
            self.editor.dimiss_open_dialogs()
