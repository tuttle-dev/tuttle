from typing import Callable, Optional

from flet import AlertDialog, Column, Container, Row

from contacts.contact_model import Contact, get_empty_contact
from core.abstractions import DialogHandler
from core.models import Address
from core.constants_and_enums import AlertDialogControls, AUTO_SCROLL
from core.views import get_primary_btn, get_headline_txt, get_std_txt_field
from core.views import CENTER_ALIGNMENT
from core.views import xsSpace
from res.dimens import MIN_WINDOW_WIDTH
from res.fonts import HEADLINE_4_SIZE


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
