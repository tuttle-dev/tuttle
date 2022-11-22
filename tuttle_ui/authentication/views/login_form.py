from typing import Callable
from flet import (
    UserControl,
    Column,
)

from res import strings, spacing
from core.views.texts import get_std_txt_field, get_std_multiline_field, get_error_txt
from core.views.buttons import get_primary_btn
from core.views.flet_constants import (
    KEYBOARD_NAME,
    KEYBOARD_EMAIL,
    KEYBOARD_ADDRESS,
    KEYBOARD_TEXT,
    KEYBOARD_PHONE,
)

from authentication.abstractions import AuthIntentsResult


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
        self.address = ""
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

    def on_change_address(self, e):
        self.address = e.control.value

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
                address=self.address,
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
        self.addressField = get_std_multiline_field(
            self.on_change_address,
            lbl=strings.ADDRESS_LBL,
            hint=strings.ADDRESS_HINT_OPTIONAL,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_ADDRESS,
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
                self.addressField,
                self.loginErrTxt,
                self.submitBtn,
            ],
        )

        return self.form
