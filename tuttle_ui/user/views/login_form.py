from typing import Callable
from flet import (
    UserControl,
    Column,
    Row,
)

from res import strings, spacing
from core.views.texts import get_std_txt_field, get_std_multiline_field, get_error_txt
from core.views.buttons import get_primary_btn
from core.views.flet_constants import (
    KEYBOARD_NAME,
    KEYBOARD_EMAIL,
    KEYBOARD_TEXT,
    KEYBOARD_PHONE,
    KEYBOARD_NUMBER,
    CENTER_ALIGNMENT,
)

from user.abstractions import AuthIntentsResult


class LoginForm(UserControl):
    """Login form to set required user info"""

    def __init__(
        self,
        onLoggedIn: Callable[[any], None],
        onLogInClicked: Callable[[str, str, str, str, str], AuthIntentsResult],
    ):
        super().__init__()
        self.formError = ""
        self.name = ""
        self.email = ""
        self.phone = ""
        self.title = ""
        self.street = ""
        self.streetNumber = ""
        self.postalCode = ""
        self.city = ""
        self.country = ""
        self.onLogInClicked = onLogInClicked
        self.onLoggedIn = onLoggedIn

    def on_field_focus(self, e):
        """Called when a field receives focus
        Clears error messages
        """
        self.nameField.error_text = ""
        self.emailField.error_text = ""
        self.phoneField.error_text = ""
        self.titleField.error_text = ""
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
        self.streetNumber = e.control.value

    def on_postal_code_changed(self, e):
        self.postalCode = e.control.value

    def on_city_changed(self, e):
        self.city = e.control.value

    def on_country_changed(self, e):
        self.country = e.control.value

    def on_submit_btn_clicked(self, e):
        # prevent multiple clicking
        self.submitBtn.disabled = True

        # hide any errors
        self.loginErrTxt.visible = False
        self.formError = ""

        missingRequiredDataErr = ""
        if len(self.name.strip()) == 0:
            missingRequiredDataErr = strings.MISSING_NAME_ERR
            self.nameField.error_text = missingRequiredDataErr
        elif len(self.email.strip()) == 0:
            missingRequiredDataErr = strings.MISSING_EMAIL_ERR
            self.emailField.error_text = missingRequiredDataErr
        elif len(self.phone.strip()) == 0:
            missingRequiredDataErr = strings.MISSING_PHONE_ERR
            self.phoneField.error_text = missingRequiredDataErr
        elif len(self.title.strip()) == 0:
            missingRequiredDataErr = strings.TITLE_NOT_SET_ERR
            self.titleField.error_text = missingRequiredDataErr

        if not missingRequiredDataErr:
            # save user
            result: AuthIntentsResult = self.onLogInClicked(
                title=self.title,
                name=self.name,
                email=self.email,
                phone=self.phone,
                street=self.street,
                streetNum=self.streetNumber,
                postalCode=self.postalCode,
                city=self.city,
                country=self.country,
            )
            if not result.wasIntentSuccessful:
                self.formError = result.errorMsg
                self.loginErrTxt.value = self.formError
                self.loginErrTxt.visible = True
                self.submitBtn.disabled = False
                self.update()
            else:
                # user is authenticated
                self.onLoggedIn(result.data)
        else:
            self.submitBtn.disabled = False
            self.update()

    def build(self):
        """Called when form is built"""
        self.nameField = get_std_txt_field(
            self.on_change_name,
            strings.NAME_LBL,
            strings.NAME_HINT,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_NAME,
        )
        self.emailField = get_std_txt_field(
            self.on_change_email,
            strings.EMAIL_LBL,
            strings.EMAIL_HINT,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_EMAIL,
        )
        self.phoneField = get_std_txt_field(
            self.on_change_phone,
            strings.PHONE_LBL,
            strings.PHONE_HINT,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_PHONE,
        )
        self.titleField = get_std_txt_field(
            self.on_change_title,
            strings.TITLE_LBL,
            strings.TITLE_HINT,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_TEXT,
        )
        self.streetField = get_std_txt_field(
            onChangeCallback=self.on_street_changed,
            lbl=strings.STREET,
            keyboardType=KEYBOARD_TEXT,
            expand=1,
        )
        self.streetNumberField = get_std_txt_field(
            onChangeCallback=self.on_street_num_changed,
            lbl=strings.STREET_NUM,
            keyboardType=KEYBOARD_NUMBER,
            expand=1,
        )
        self.postalCodeField = get_std_txt_field(
            onChangeCallback=self.on_postal_code_changed,
            lbl=strings.POSTAL_CODE,
            keyboardType=KEYBOARD_NUMBER,
            expand=1,
        )

        self.cityField = get_std_txt_field(
            onChangeCallback=self.on_city_changed,
            lbl=strings.CITY,
            keyboardType=KEYBOARD_TEXT,
            expand=1,
        )
        self.countryField = get_std_txt_field(
            onChangeCallback=self.on_country_changed,
            lbl=strings.COUNTRY,
            keyboardType=KEYBOARD_TEXT,
        )
        self.loginErrTxt = get_error_txt(self.formError)
        self.submitBtn = get_primary_btn(
            onClickCallback=self.on_submit_btn_clicked,
            label=strings.GET_STARTED,
        )
        self.form = Column(
            spacing=spacing.SPACE_MD,
            controls=[
                self.titleField,
                self.nameField,
                self.emailField,
                self.phoneField,
                Row(
                    vertical_alignment=CENTER_ALIGNMENT,
                    controls=[
                        self.streetField,
                        self.streetNumberField,
                    ],
                ),
                Row(
                    vertical_alignment=CENTER_ALIGNMENT,
                    controls=[
                        self.postalCodeField,
                        self.cityField,
                    ],
                ),
                self.countryField,
                self.loginErrTxt,
                self.submitBtn,
            ],
        )

        return self.form
