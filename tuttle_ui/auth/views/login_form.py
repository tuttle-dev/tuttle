from typing import Callable
from flet import (
    UserControl,
    Column,
    Row,
)

from res import strings, dimens
from core.views import (
    get_std_txt_field,
    get_error_txt,
    get_primary_btn,
    get_secondary_btn,
)
from core.constants_and_enums import (
    KEYBOARD_NAME,
    KEYBOARD_EMAIL,
    KEYBOARD_TEXT,
    KEYBOARD_PHONE,
    KEYBOARD_NUMBER,
    CENTER_ALIGNMENT,
)

from core.models import IntentResult


class LoginForm(UserControl):
    """Login form to set required user info"""

    def __init__(
        self,
        on_logged_in,
        on_save_user,
    ):
        super().__init__()
        self.form_error = ""
        self.name = ""
        self.email = ""
        self.phone = ""
        self.title = ""
        self.street = ""
        self.street_number = ""
        self.postal_code = ""
        self.city = ""
        self.country = ""
        self.on_save_user = on_save_user
        self.on_logged_in = on_logged_in

    def on_field_focus(self, e):
        """Called when a field receives focus
        Clears error messages
        """
        self.name_field.error_text = ""
        self.email_field.error_text = ""
        self.phone_field.error_text = ""
        self.title_field.error_text = ""
        self.update()

    def on_change_name(self, e):
        self.name = e.control.value

    def on_change_email(self, e):
        self.email = e.control.value

    def on_change_title(self, e):
        self.title = e.control.value

    def on_change_phone(self, e):
        self.phone = e.control.value

    def on_street_changed(self, e):
        self.street = e.control.value

    def on_street_num_changed(self, e):
        self.street_number = e.control.value

    def on_postal_code_changed(self, e):
        self.postal_code = e.control.value

    def on_city_changed(self, e):
        self.city = e.control.value

    def on_country_changed(self, e):
        self.country = e.control.value

    def on_skip_btn_clicked(self, e):
        """Skip the login form and go to the main screen"""
        self.on_logged_in()

    def on_submit_btn_clicked(self, e):
        # prevent multiple clicking
        self.submit_btn.disabled = True

        # hide any errors
        self.login_err_txt.visible = False
        self.form_error = ""

        missingRequiredDataErr = ""
        if len(self.name.strip()) == 0:
            missingRequiredDataErr = strings.MISSING_NAME_ERR
            self.name_field.error_text = missingRequiredDataErr
        elif len(self.email.strip()) == 0:
            missingRequiredDataErr = strings.MISSING_EMAIL_ERR
            self.email_field.error_text = missingRequiredDataErr
        elif len(self.phone.strip()) == 0:
            missingRequiredDataErr = strings.MISSING_PHONE_ERR
            self.phone_field.error_text = missingRequiredDataErr
        elif len(self.title.strip()) == 0:
            missingRequiredDataErr = strings.TITLE_NOT_SET_ERR
            self.title_field.error_text = missingRequiredDataErr

        if not missingRequiredDataErr:
            # save user
            result: IntentResult = self.on_save_user(
                title=self.title,
                name=self.name,
                email=self.email,
                phone=self.phone,
                street=self.street,
                street_num=self.street_number,
                postal_code=self.postal_code,
                city=self.city,
                country=self.country,
            )
            if not result.was_intent_successful:
                self.form_error = result.error_msg
                self.login_err_txt.value = self.form_error
                self.login_err_txt.visible = True
                self.submit_btn.disabled = False
                self.update()
            else:
                # user is authenticated
                self.on_logged_in()
        else:
            self.submit_btn.disabled = False
            self.update()

    def build(self):
        """Called when form is built"""
        self.name_field = get_std_txt_field(
            self.on_change_name,
            strings.NAME_LBL,
            strings.NAME_HINT,
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_NAME,
        )
        self.email_field = get_std_txt_field(
            self.on_change_email,
            strings.EMAIL_LBL,
            strings.EMAIL_HINT,
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_EMAIL,
        )
        self.phone_field = get_std_txt_field(
            self.on_change_phone,
            strings.PHONE_LBL,
            strings.PHONE_HINT,
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_PHONE,
        )
        self.title_field = get_std_txt_field(
            self.on_change_title,
            strings.TITLE_LBL,
            strings.TITLE_HINT,
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_TEXT,
        )
        self.street_field = get_std_txt_field(
            on_change=self.on_street_changed,
            lbl=strings.STREET,
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.street_number_field = get_std_txt_field(
            on_change=self.on_street_num_changed,
            lbl=strings.STREET_NUM,
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )
        self.postal_code_field = get_std_txt_field(
            on_change=self.on_postal_code_changed,
            lbl=strings.POSTAL_CODE,
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )

        self.city_field = get_std_txt_field(
            on_change=self.on_city_changed,
            lbl=strings.CITY,
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.country_field = get_std_txt_field(
            on_change=self.on_country_changed,
            lbl=strings.COUNTRY,
            keyboard_type=KEYBOARD_TEXT,
        )
        self.login_err_txt = get_error_txt(self.form_error)
        self.submit_btn = get_primary_btn(
            on_click=self.on_submit_btn_clicked,
            label=strings.GET_STARTED,
        )
        self.skip_button = get_secondary_btn(
            on_click=self.on_skip_btn_clicked,
            label="Skip",
        )
        self.form = Column(
            spacing=dimens.SPACE_MD,
            controls=[
                self.title_field,
                self.name_field,
                self.email_field,
                self.phone_field,
                Row(
                    vertical_alignment=CENTER_ALIGNMENT,
                    controls=[
                        self.street_field,
                        self.street_number_field,
                    ],
                ),
                Row(
                    vertical_alignment=CENTER_ALIGNMENT,
                    controls=[
                        self.postal_code_field,
                        self.city_field,
                    ],
                ),
                self.country_field,
                self.login_err_txt,
                self.submit_btn,
                self.skip_button,
            ],
        )

        return self.form
