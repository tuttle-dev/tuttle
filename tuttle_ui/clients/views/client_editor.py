from typing import Callable, Optional

from flet import AlertDialog, Column, Container, Row, UserControl

from core.abstractions import DialogHandler
from core.constants_and_enums import AlertDialogControls, AUTO_SCROLL
from core.views import (
    get_primary_btn,
    get_headline_txt,
    get_std_txt_field,
    get_dropdown,
)

from core.views import CENTER_ALIGNMENT
from core.views import xsSpace
from res.dimens import MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from res.fonts import HEADLINE_4_SIZE, SUBTITLE_2_SIZE, BODY_1_SIZE
from res.colors import GRAY_COLOR
from clients.client_model import Client, get_empty_client
from contacts.contact_model import Contact, get_empty_contact
from core.models import get_empty_address


class ClientEditorPopUp(DialogHandler, UserControl):
    """Pop up used for editing a client"""

    def __init__(
        self,
        dialog_controller: Callable[[any, AlertDialogControls], None],
        on_submit: Callable,
        contacts_map,
        client: Optional[Client] = None,
    ):
        self.dialog_height = MIN_WINDOW_HEIGHT
        self.dialog_width = int(MIN_WINDOW_WIDTH * 0.8)
        self.half_of_dialog_width = int(MIN_WINDOW_WIDTH * 0.35)

        # initialize the data

        self.client = client if client is not None else get_empty_client()
        self.invoicing_contact = (
            self.client.invoicing_contact
            if self.client.invoicing_contact is not None
            else get_empty_contact()
        )
        self.address = (
            self.invoicing_contact.address
            if self.invoicing_contact.address is not None
            else get_empty_address()
        )
        self.contacts_as_map = contacts_map
        self.contact_options = self.get_contacts_as_list()

        title = "Edit Client" if client is not None else "New Client"

        initial_selected_contact = self.get_contact_dropdown_item(
            self.invoicing_contact.id
        )

        self.first_name_field = get_std_txt_field(
            on_change=self.on_fname_changed,
            lbl="First Name",
            hint=self.invoicing_contact.first_name,
            initial_value=self.invoicing_contact.first_name,
        )

        self.last_name_field = get_std_txt_field(
            on_change=self.on_lname_changed,
            lbl="Last Name",
            hint=self.invoicing_contact.last_name,
            initial_value=self.invoicing_contact.last_name,
        )
        self.company_field = get_std_txt_field(
            on_change=self.on_company_changed,
            lbl="Company",
            hint=self.invoicing_contact.company,
            initial_value=self.invoicing_contact.company,
        )
        self.email_field = get_std_txt_field(
            on_change=self.on_email_changed,
            lbl="Email",
            hint=self.invoicing_contact.email,
            initial_value=self.invoicing_contact.email,
        )

        self.street_field = get_std_txt_field(
            on_change=self.on_street_changed,
            lbl="Street",
            hint=self.invoicing_contact.address.street,
            initial_value=self.invoicing_contact.address.street,
            width=self.half_of_dialog_width,
        )
        self.street_num_field = get_std_txt_field(
            on_change=self.on_street_num_changed,
            lbl="Street No.",
            hint=self.invoicing_contact.address.number,
            initial_value=self.invoicing_contact.address.number,
            width=self.half_of_dialog_width,
        )
        self.postal_code_field = get_std_txt_field(
            on_change=self.on_postal_code_changed,
            lbl="Postal code",
            hint=self.invoicing_contact.address.postal_code,
            initial_value=self.invoicing_contact.address.postal_code,
            width=self.half_of_dialog_width,
        )
        self.city_field = get_std_txt_field(
            on_change=self.on_city_changed,
            lbl="City",
            hint=self.invoicing_contact.address.city,
            initial_value=self.invoicing_contact.address.city,
            width=self.half_of_dialog_width,
        )
        self.country_field = get_std_txt_field(
            on_change=self.on_country_changed,
            lbl="Country",
            hint=self.invoicing_contact.address.country,
            initial_value=self.invoicing_contact.address.country,
        )

        dialog = AlertDialog(
            content=Container(
                height=self.dialog_height,
                content=Column(
                    scroll=AUTO_SCROLL,
                    controls=[
                        get_headline_txt(txt=title, size=HEADLINE_4_SIZE),
                        xsSpace,
                        get_std_txt_field(
                            on_change=self.on_title_changed,
                            lbl="Client's title",
                            hint=self.client.title,
                            initial_value=self.client.title,
                        ),
                        xsSpace,
                        get_headline_txt(
                            txt="Invoicing Contact",
                            size=SUBTITLE_2_SIZE,
                            color=GRAY_COLOR,
                        ),
                        xsSpace,
                        get_dropdown(
                            on_change=self.on_contact_selected,
                            lbl="Select contact",
                            items=self.contact_options,
                            initial_value=initial_selected_contact,
                        ),
                        xsSpace,
                        self.first_name_field,
                        self.last_name_field,
                        self.company_field,
                        self.email_field,
                        Row(
                            vertical_alignment=CENTER_ALIGNMENT,
                            controls=[self.street_field, self.street_num_field],
                        ),
                        Row(
                            vertical_alignment=CENTER_ALIGNMENT,
                            controls=[
                                self.postal_code_field,
                                self.city_field,
                            ],
                        ),
                        self.country_field,
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
        self.title = ""
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

    def get_contacts_as_list(self):
        """transforms a map of id-contact_name to a list for dropdown options"""
        contacts_list = []
        for key in self.contacts_as_map:
            item = self.get_contact_dropdown_item(key)
            if item:
                contacts_list.append(item)
        return contacts_list

    def get_contact_dropdown_item(self, key):
        if key is not None and key in self.contacts_as_map:
            return f"#{key} {self.contacts_as_map[key].name}"
        return ""

    def on_contact_selected(self, e):
        # parse selected value to extract id
        selected = e.control.value
        id = ""
        for c in selected:
            if c == "#":
                continue
            if c == " ":
                break
            id = id + c
        if int(id) in self.contacts_as_map:
            self.invoicing_contact: Contact = self.contacts_as_map[int(id)]
            self.set_invoicing_contact_fields()

    def set_invoicing_contact_fields(self):
        self.first_name_field.value = self.invoicing_contact.first_name
        self.last_name_field.value = self.invoicing_contact.last_name
        self.company_field.value = self.invoicing_contact.company
        self.email_field.value = self.invoicing_contact.email
        self.street_field.value = self.invoicing_contact.address.street
        self.street_num_field.value = self.invoicing_contact.address.number
        self.postal_code_field.value = self.invoicing_contact.address.postal_code
        self.city_field.value = self.invoicing_contact.address.city
        self.country_field.value = self.invoicing_contact.address.country
        self.dialog.update()

    def on_title_changed(self, e):
        self.title = e.control.value

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
        self.client.title = (
            self.title.strip() if self.title.strip() else self.client.title
        )
        self.invoicing_contact.first_name = (
            self.fname.strip()
            if self.fname.strip()
            else self.invoicing_contact.first_name
        )
        self.invoicing_contact.last_name = (
            self.lname.strip()
            if self.lname.strip()
            else self.invoicing_contact.last_name
        )
        self.invoicing_contact.company = (
            self.company.strip()
            if self.company.strip()
            else self.invoicing_contact.company
        )
        self.invoicing_contact.email = (
            self.email.strip() if self.email.strip() else self.invoicing_contact.email
        )
        self.address.street = (
            self.street.strip()
            if self.street.strip()
            else self.invoicing_contact.address.street
        )

        self.address.number = (
            self.street_num.strip()
            if self.street_num.strip()
            else self.invoicing_contact.address.number
        )
        self.address.postal_code = (
            self.postal_code.strip()
            if self.postal_code.strip()
            else self.invoicing_contact.address.postal_code
        )
        self.address.city = (
            self.city.strip()
            if self.city.strip()
            else self.invoicing_contact.address.city
        )
        self.address.country = (
            self.country.strip()
            if self.country.strip()
            else self.invoicing_contact.address.country
        )
        self.invoicing_contact.address = self.address
        self.client.invoicing_contact = self.invoicing_contact
        self.close_dialog()
        self.on_submit(self.client)

    def build(self):
        return self.dialog
