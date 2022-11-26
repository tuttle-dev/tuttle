import typing
from typing import Callable

from flet import (
    Card,
    Column,
    Container,
    IconButton,
    ResponsiveRow,
    Row,
    icons,
    margin,
    padding,
)
from user.user_model import User
from user.abstractions import AuthView
from user.auth_intent_impl import AuthIntentImpl
from core.abstractions import LocalCache
from core.views.flet_constants import (
    CENTER_ALIGNMENT,
    KEYBOARD_EMAIL,
    KEYBOARD_NAME,
    KEYBOARD_NUMBER,
    KEYBOARD_PHONE,
    KEYBOARD_TEXT,
)
from core.views.progress_bars import horizontalProgressBar
from core.views.spacers import stdSpace
from core.views.texts import get_headline_txt, get_std_txt_field, get_error_txt
from core.views.buttons import get_primary_btn
from res import spacing
from res.fonts import HEADLINE_4_SIZE
from res.strings import (
    PROFILE,
    UPDATE_PROFILE,
    PHONE_LBL,
    PHONE_HINT,
    STREET,
    STREET_NUM,
    TITLE_LBL,
    TITLE_HINT,
    POSTAL_CODE,
    CITY,
    COUNTRY,
    NAME_LBL,
    EMAIL_HINT,
    EMAIL_LBL,
    NAME_HINT,
    MISSING_NAME_ERR,
    MISSING_EMAIL_ERR,
    MISSING_PHONE_ERR,
    TITLE_NOT_SET_ERR,
    UPDATED_PROFILE_SUCCESS,
)


class ProfileScreen(AuthView):
    def __init__(
        self,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        localCacheHandler: LocalCache,
        dialogController: Callable,
        showSnackCallback: Callable,
        onNavigateBack: Callable,
    ):
        super().__init__(
            changeRouteCallback=changeRouteCallback,
            intentHandler=AuthIntentImpl(cache=localCacheHandler),
        )
        self.pageDialogController = dialogController
        self.showSnack = showSnackCallback
        self.keepBackStack = True
        self.onNavigateBack = onNavigateBack
        self.name = ""
        self.email = ""
        self.phone = ""
        self.title = ""
        self.street = ""
        self.streetNumber = ""
        self.postalCode = ""
        self.city = ""
        self.country = ""

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

    def on_update_btn_clicked(self, e):
        if not self.user:
            # user is not loaded yet
            return

        # prevent multiple submissions
        self.updateBtn.disabled = True
        self.progressBar.visible = True
        self.update()

        missingRequiredDataErr = ""
        if len(self.name.strip()) == 0:
            missingRequiredDataErr = MISSING_NAME_ERR
            self.nameField.error_text = missingRequiredDataErr
        elif len(self.email.strip()) == 0:
            missingRequiredDataErr = MISSING_EMAIL_ERR
            self.emailField.error_text = missingRequiredDataErr
        elif len(self.phone.strip()) == 0:
            missingRequiredDataErr = MISSING_PHONE_ERR
            self.phoneField.error_text = missingRequiredDataErr
        elif len(self.title.strip()) == 0:
            missingRequiredDataErr = TITLE_NOT_SET_ERR
            self.titleField.error_text = missingRequiredDataErr

        if missingRequiredDataErr:
            self.showSnack(missingRequiredDataErr, True)
        else:
            # save user
            result = self.intentHandler.update_user(
                user=self.user,
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
                self.showSnack(result.errorMsg, True)
            else:
                self.showSnack(UPDATED_PROFILE_SUCCESS, False)
                self.user: User = result.data
                self.refresh_user_info()
        self.updateBtn.disabled = False
        self.progressBar.visible = False
        self.update()

    def set_profile_form(self):
        self.nameField = get_std_txt_field(
            self.on_change_name,
            NAME_LBL,
            NAME_HINT,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_NAME,
        )
        self.emailField = get_std_txt_field(
            self.on_change_email,
            EMAIL_LBL,
            EMAIL_HINT,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_EMAIL,
        )
        self.phoneField = get_std_txt_field(
            self.on_change_phone,
            PHONE_LBL,
            PHONE_HINT,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_PHONE,
        )
        self.titleField = get_std_txt_field(
            self.on_change_title,
            TITLE_LBL,
            TITLE_HINT,
            onFocusCallback=self.on_field_focus,
            keyboardType=KEYBOARD_TEXT,
        )
        self.streetField = get_std_txt_field(
            onChangeCallback=self.on_street_changed,
            lbl=STREET,
            keyboardType=KEYBOARD_TEXT,
            expand=1,
        )
        self.streetNumberField = get_std_txt_field(
            onChangeCallback=self.on_street_num_changed,
            lbl=STREET_NUM,
            keyboardType=KEYBOARD_NUMBER,
            expand=1,
        )
        self.postalCodeField = get_std_txt_field(
            onChangeCallback=self.on_postal_code_changed,
            lbl=POSTAL_CODE,
            keyboardType=KEYBOARD_NUMBER,
            expand=1,
        )

        self.cityField = get_std_txt_field(
            onChangeCallback=self.on_city_changed,
            lbl=CITY,
            keyboardType=KEYBOARD_TEXT,
            expand=1,
        )

        self.countryField = get_std_txt_field(
            onChangeCallback=self.on_country_changed,
            lbl=COUNTRY,
            keyboardType=KEYBOARD_TEXT,
        )

        self.updateBtn = get_primary_btn(
            onClickCallback=self.on_update_btn_clicked,
            label=UPDATE_PROFILE,
        )
        self.profileForm = Column(
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
                self.updateBtn,
            ],
        )

    def build(self):
        self.progressBar = horizontalProgressBar
        self.progressBar.visible = False
        self.set_profile_form()
        self.formContainer = Column(
            spacing=spacing.SPACE_STD,
            run_spacing=0,
            controls=[
                Row(
                    spacing=spacing.SPACE_STD,
                    run_spacing=0,
                    vertical_alignment=CENTER_ALIGNMENT,
                    controls=[
                        IconButton(
                            icon=icons.KEYBOARD_ARROW_LEFT, on_click=self.onNavigateBack
                        ),
                        get_headline_txt(PROFILE, size=HEADLINE_4_SIZE),
                    ],
                ),
                Container(
                    self.progressBar,
                    margin=margin.symmetric(horizontal=spacing.SPACE_MD),
                ),
                self.profileForm,
            ],
        )
        view = Container(
            margin=margin.all(spacing.SPACE_MD),
            content=ResponsiveRow(
                spacing=0,
                run_spacing=0,
                alignment=CENTER_ALIGNMENT,
                vertical_alignment=CENTER_ALIGNMENT,
                controls=[
                    Card(
                        Container(
                            padding=padding.all(spacing.SPACE_MD),
                            content=self.formContainer,
                        ),
                        col={"xs": 12, "md": 6},
                    ),
                ],
            ),
        )
        return view

    def did_mount(self):
        super().did_mount()
        self.progressBar.visible = True
        self.update()
        result = self.intentHandler.get_user_profile()
        if not result.wasIntentSuccessful:
            self.showSnack(result.errorMsg, True)
        else:
            self.user: User = result.data
            self.refresh_user_info()
        self.progressBar.visible = False
        self.update()

    def refresh_user_info(self):
        if not self.user:
            return
        self.name = self.user.name
        self.email = self.user.email
        self.phone = self.user.phone
        self.title = self.user.title
        if self.user.address:
            self.street = self.user.address.street
            self.streetNumber = self.user.address.number
            self.postalCode = self.user.address.postal_code
            self.city = self.user.address.city
            self.country = self.user.address.country
        self.nameField.value = self.name
        self.emailField.value = self.email
        self.phoneField.value = self.phone
        self.titleField.value = self.title
        self.streetField.value = self.street
        self.streetNumberField.value = self.street
        self.postalCodeField.value = self.postalCode
        self.streetNumberField.value = self.streetNumber
        self.cityField.value = self.city
        self.countryField.value = self.country
