from typing import Callable

from flet import AlertDialog, Column, Container, Row

from contacts.contact_model import Contact, get_empty_contact
from core.abstractions import DialogHandler
from core.models import get_empty_address
from core.views import texts
from core.views.alert_dialog_controls import AlertDialogControls
from core.views.buttons import get_primary_btn
from core.views.flet_constants import CENTER_ALIGNMENT
from core.views.spacers import xsSpace
from res.dimens import MIN_WINDOW_WIDTH
from res.fonts import HEADLINE_4_SIZE


class NewContactPopUp(DialogHandler):
    """Pop up used for editing a contact"""

    def __init__(
        self,
        dialogController: Callable[[any, AlertDialogControls], None],
        onSubmit: Callable,
    ):
        dialogHeight = 550
        dialogWidth = int(MIN_WINDOW_WIDTH * 0.8)
        halfOfDialogWidth = int(MIN_WINDOW_WIDTH * 0.35)
        self.address = get_empty_address()
        self.contact: Contact = get_empty_contact(self.address)
        dialog = AlertDialog(
            content=Container(
                height=dialogHeight,
                content=Column(
                    controls=[
                        texts.get_headline_txt(
                            txt="Edit contact", size=HEADLINE_4_SIZE
                        ),
                        xsSpace,
                        texts.get_std_txt_field(
                            onChangeCallback=self.on_fname_changed,
                            lbl="First Name",
                            hint=self.contact.first_name,
                            initialValue=self.contact.first_name,
                        ),
                        texts.get_std_txt_field(
                            onChangeCallback=self.on_lname_changed,
                            lbl="Last Name",
                            hint=self.contact.last_name,
                            initialValue=self.contact.last_name,
                        ),
                        texts.get_std_txt_field(
                            onChangeCallback=self.on_company_changed,
                            lbl="Company",
                            hint=self.contact.company,
                            initialValue=self.contact.company,
                        ),
                        texts.get_std_txt_field(
                            onChangeCallback=self.on_email_changed,
                            lbl="Email",
                            hint=self.contact.email,
                            initialValue=self.contact.email,
                        ),
                        Row(
                            vertical_alignment=CENTER_ALIGNMENT,
                            controls=[
                                texts.get_std_txt_field(
                                    onChangeCallback=self.on_street_changed,
                                    lbl="Street",
                                    hint=self.contact.address.street,
                                    initialValue=self.contact.address.street,
                                    width=halfOfDialogWidth,
                                ),
                                texts.get_std_txt_field(
                                    onChangeCallback=self.on_street_num_changed,
                                    lbl="Street No.",
                                    hint=self.contact.address.number,
                                    initialValue=self.contact.address.number,
                                    width=halfOfDialogWidth,
                                ),
                            ],
                        ),
                        Row(
                            vertical_alignment=CENTER_ALIGNMENT,
                            controls=[
                                texts.get_std_txt_field(
                                    onChangeCallback=self.on_postal_code_changed,
                                    lbl="Postal code",
                                    hint=self.contact.address.postal_code,
                                    initialValue=self.contact.address.postal_code,
                                    width=halfOfDialogWidth,
                                ),
                                texts.get_std_txt_field(
                                    onChangeCallback=self.on_city_changed,
                                    lbl="City",
                                    hint=self.contact.address.city,
                                    initialValue=self.contact.address.city,
                                    width=halfOfDialogWidth,
                                ),
                            ],
                        ),
                        texts.get_std_txt_field(
                            onChangeCallback=self.on_country_changed,
                            lbl="Country",
                            hint=self.contact.address.country,
                            initialValue=self.contact.address.country,
                        ),
                        xsSpace,
                    ]
                ),
                width=dialogWidth,
            ),
            actions=[
                get_primary_btn(
                    label="Done", onClickCallback=self.on_submit_btn_clicked
                ),
            ],
        )
        super().__init__(dialog=dialog, dialogController=dialogController)

        self.fname = ""
        self.lname = ""
        self.company = ""
        self.email = ""
        self.street = ""
        self.street_num = ""
        self.postal_code = ""
        self.city = ""
        self.country = ""
        self.onSubmit = onSubmit

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
        self.contact.first_name = self.fname.strip()
        self.contact.last_name = self.lname.strip()
        self.contact.company = self.company.strip()
        self.contact.email = self.email.strip()
        self.address.street = self.street.strip()
        self.address.number = self.street_num.strip()
        self.address.postal_code = self.postal_code.strip()
        self.address.city = self.city.strip()
        self.address.country = self.country.strip()
        self.contact.address = self.address
        self.close_dialog()
        self.onSubmit(self.contact)
