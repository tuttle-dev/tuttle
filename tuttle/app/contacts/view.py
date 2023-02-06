from typing import Callable, Optional

from flet import (
    AlertDialog,
    Card,
    Column,
    Container,
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
from core.abstractions import DialogHandler, TView, TViewParams
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
                    size=dimens.MD_ICON_SIZE,
                ),
                title=views.TBodyText(utils.truncate_str(self.contact.name)),
                subtitle=views.TBodyText(
                    utils.truncate_str(self.contact.company), color=colors.GRAY_COLOR
                ),
                trailing=views.TContextMenu(
                    on_click_edit=lambda e: self.on_edit_clicked(self.contact),
                    on_click_delete=lambda e: self.on_deleted_clicked(self.contact),
                ),
            ),
            views.Spacer(md_space=True),
            ResponsiveRow(
                controls=[
                    views.TBodyText(
                        txt="email",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    views.TBodyText(
                        txt=self.contact.email,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                ],
                spacing=dimens.SPACE_XS,
                run_spacing=0,
                vertical_alignment=utils.CENTER_ALIGNMENT,
            ),
            views.Spacer(md_space=True),
            ResponsiveRow(
                controls=[
                    views.TBodyText(
                        txt="address",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        views.TBodyText(
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
        on_error: Callable,
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

        self.fname_field = views.TTextField(
            label="First Name",
            hint=self.contact.first_name,
            initial_value=self.contact.first_name,
        )
        self.lname_field = views.TTextField(
            label="Last Name",
            hint=self.contact.last_name,
            initial_value=self.contact.last_name,
        )
        self.company_name_field = views.TTextField(
            label="Company",
            hint=self.contact.company,
            initial_value=self.contact.company,
        )
        self.email_field = views.TTextField(
            label="Email",
            hint=self.contact.email,
            initial_value=self.contact.email,
        )
        self.street_name_field = views.TTextField(
            label="Street",
            hint=self.contact.address.street,
            initial_value=self.contact.address.street,
            width=width_spanning_half_of_container,
        )
        self.street_num_field = views.TTextField(
            label="Street No.",
            hint=self.contact.address.number,
            initial_value=self.contact.address.number,
            width=width_spanning_half_of_container,
        )

        self.postal_code_field = views.TTextField(
            label="Postal code",
            hint=self.contact.address.postal_code,
            initial_value=self.contact.address.postal_code,
            width=width_spanning_half_of_container,
        )
        self.city_field = views.TTextField(
            label="City",
            hint=self.contact.address.city,
            initial_value=self.contact.address.city,
            width=width_spanning_half_of_container,
        )
        self.country_field = views.TTextField(
            label="Country",
            hint=self.contact.address.country,
            initial_value=self.contact.address.country,
        )
        dialog = AlertDialog(
            content=Container(
                height=pop_up_height,
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.THeading(title=title, size=fonts.HEADLINE_4_SIZE),
                        views.Spacer(xs_space=True),
                        self.fname_field,
                        self.lname_field,
                        self.company_name_field,
                        self.email_field,
                        Row(
                            vertical_alignment=utils.CENTER_ALIGNMENT,
                            controls=[
                                self.street_name_field,
                                self.street_num_field,
                            ],
                        ),
                        Row(
                            vertical_alignment=utils.CENTER_ALIGNMENT,
                            controls=[
                                self.postal_code_field,
                                self.city_field,
                            ],
                        ),
                        self.country_field,
                        views.Spacer(xs_space=True),
                    ],
                ),
                width=pop_up_width,
            ),
            actions=[
                views.TPrimaryButton(label="Done", on_click=self.on_submit_btn_clicked),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)

        self.on_submit_callback = on_submit
        self.on_error_callback = on_error

    def on_submit_btn_clicked(self, e):
        """Called when the submit button is clicked"""
        # get the values from the fields
        fname = self.fname_field.value.strip()
        lname = self.lname_field.value.strip()
        company = self.company_name_field.value.strip()
        email = self.email_field.value.strip()
        street = self.street_name_field.value.strip()
        street_num = self.street_num_field.value.strip()
        postal_code = self.postal_code_field.value.strip()
        city = self.city_field.value.strip()
        country = self.country_field.value.strip()

        # update where updated else keep old value
        self.contact.first_name = fname if fname else self.contact.first_name
        self.contact.last_name = lname if lname else self.contact.last_name
        self.contact.company = company if company else self.contact.company
        self.contact.email = email if email else self.contact.email
        self.address.street = street if street else self.contact.address.street

        self.address.number = street_num if street_num else self.contact.address.number
        self.address.postal_code = (
            postal_code if postal_code else self.contact.address.postal_code
        )
        self.address.city = city if city else self.contact.address.city
        self.address.country = country if country else self.contact.address.country
        self.contact.address = self.address
        if self.contact.address.is_empty:
            self.on_error_callback("Address cannot be empty")
            return
        if not self.contact.first_name or not self.contact.last_name:
            self.on_error_callback("First and last name cannot be empty")
            return
        self.close_dialog()
        self.on_submit_callback(self.contact)


class ContactsListView(TView, UserControl):
    """The view for the contacts list page"""

    def __init__(self, params: TViewParams):
        super().__init__(params)
        self.intent = ContactsIntent()
        self.loading_indicator = views.TProgressBar()
        self.no_contacts_control = views.TBodyText(
            txt="You have not added any contacts yet",
            color=colors.ERROR_COLOR,
            show=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.THeading(title="My Contacts", size=fonts.HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.no_contacts_control,
                    ],
                )
            ]
        )
        self.contacts_container = views.THomeGrid()
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
                on_error=lambda error: self.show_snack(error, is_error=True),
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
            on_error=lambda error: self.show_snack(error, is_error=True),
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
                views.Spacer(md_space=True),
                Container(self.contacts_container, expand=True),
            ]
        )

    def will_unmount(self):
        """Called when the view is unmounted"""
        self.mounted = False
        if self.editor:
            self.editor.dimiss_open_dialogs()
