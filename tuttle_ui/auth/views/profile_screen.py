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
from core.models import IntentResult
from auth.user_model import User
from auth.auth_intent_impl import AuthIntentImpl
from core.abstractions import ClientStorage, TuttleView
from core.constants_and_enums import (
    CENTER_ALIGNMENT,
    KEYBOARD_EMAIL,
    KEYBOARD_NAME,
    KEYBOARD_NUMBER,
    KEYBOARD_PHONE,
    KEYBOARD_TEXT,
)
from core.views import horizontal_progress
from core.views import stdSpace
from core.views import get_headline_txt, get_std_txt_field, get_error_txt
from core.views import get_primary_btn
from res import dimens
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
from flet import UserControl


class ProfileScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        on_navigate_back,
        local_storage,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            on_navigate_back=on_navigate_back,
            horizontal_alignment_in_parent=CENTER_ALIGNMENT,
        )
        self.intent_handler = AuthIntentImpl(local_storage=local_storage)
        self.name = ""
        self.email = ""
        self.phone = ""
        self.title = ""
        self.street = ""
        self.street_number = ""
        self.postal_code = ""
        self.city = ""
        self.country = ""

    def on_field_focus(self, e):
        """Called when a field receives focus
        Clears error messages
        """
        self.name_field.error_text = ""
        self.email_field.error_text = ""
        self.phone_field.error_text = ""
        self.title_field.error_text = ""
        if self.mounted:
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

    def on_update_btn_clicked(self, e):

        if self.user is None:
            # user is not loaded yet
            return

        # prevent multiple submissions
        self.update_btn.disabled = True
        self.progressBar.visible = True
        if self.mounted:
            self.update()

        missingRequiredDataErr = ""
        if len(self.name.strip()) == 0:
            missingRequiredDataErr = MISSING_NAME_ERR
            self.name_field.error_text = missingRequiredDataErr
        elif len(self.email.strip()) == 0:
            missingRequiredDataErr = MISSING_EMAIL_ERR
            self.email_field.error_text = missingRequiredDataErr
        elif len(self.phone.strip()) == 0:
            missingRequiredDataErr = MISSING_PHONE_ERR
            self.phone_field.error_text = missingRequiredDataErr
        elif len(self.title.strip()) == 0:
            missingRequiredDataErr = TITLE_NOT_SET_ERR
            self.title_field.error_text = missingRequiredDataErr

        if missingRequiredDataErr:
            self.show_snack(missingRequiredDataErr, True)
        else:
            # save user
            result: IntentResult = self.intent_handler.update_user(
                user=self.user,
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
                self.show_snack(result.error_msg, True)
            else:
                self.show_snack(UPDATED_PROFILE_SUCCESS, False)
                self.user: User = result.data
                self.refresh_user_info()
        self.update_btn.disabled = False
        self.progressBar.visible = False
        self.update()

    def set_profile_form(self):
        self.name_field = get_std_txt_field(
            self.on_change_name,
            NAME_LBL,
            NAME_HINT,
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_NAME,
        )
        self.email_field = get_std_txt_field(
            self.on_change_email,
            EMAIL_LBL,
            EMAIL_HINT,
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_EMAIL,
        )
        self.phone_field = get_std_txt_field(
            self.on_change_phone,
            PHONE_LBL,
            PHONE_HINT,
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_PHONE,
        )
        self.title_field = get_std_txt_field(
            self.on_change_title,
            TITLE_LBL,
            TITLE_HINT,
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_TEXT,
        )
        self.street_field = get_std_txt_field(
            on_change=self.on_street_changed,
            lbl=STREET,
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.street_number_field = get_std_txt_field(
            on_change=self.on_street_num_changed,
            lbl=STREET_NUM,
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )
        self.postal_code_field = get_std_txt_field(
            on_change=self.on_postal_code_changed,
            lbl=POSTAL_CODE,
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )

        self.city_field = get_std_txt_field(
            on_change=self.on_city_changed,
            lbl=CITY,
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )

        self.country_field = get_std_txt_field(
            on_change=self.on_country_changed,
            lbl=COUNTRY,
            keyboard_type=KEYBOARD_TEXT,
        )

        self.update_btn = get_primary_btn(
            on_click=self.on_update_btn_clicked,
            label=UPDATE_PROFILE,
        )
        self.profile_form = Column(
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
                self.update_btn,
            ],
        )

    def did_mount(self):
        try:
            self.mounted = True
            self.progressBar.visible = True
            self.update()
            result: IntentResult = self.intent_handler.get_user()
            if not result.was_intent_successful:
                self.show_snack(result.error_msg, True)
            else:
                self.user: User = result.data
                self.refresh_user_info()
            self.progressBar.visible = False
            self.update()
        except Exception as e:
            # log error
            print(f"exception raised @profile_screen.did_mount {e}")

    def refresh_user_info(self):
        if self.user is None:
            return
        self.name = self.user.name
        self.email = self.user.email
        self.phone = self.user.phone_number
        self.title = self.user.subtitle
        if self.user.address:
            self.street = self.user.address.street
            self.street_number = self.user.address.number
            self.postal_code = self.user.address.postal_code
            self.city = self.user.address.city
            self.country = self.user.address.country
        self.name_field.value = self.name
        self.email_field.value = self.email
        self.phone_field.value = self.phone
        self.title_field.value = self.title
        self.street_field.value = self.street
        self.street_number_field.value = self.street
        self.postal_code_field.value = self.postal_code
        self.street_number_field.value = self.street_number
        self.city_field.value = self.city
        self.country_field.value = self.country

    def build(self):
        self.progressBar = horizontal_progress
        self.progressBar.visible = False
        self.set_profile_form()
        self.form_container = Column(
            spacing=dimens.SPACE_STD,
            run_spacing=0,
            controls=[
                Row(
                    spacing=dimens.SPACE_STD,
                    run_spacing=0,
                    vertical_alignment=CENTER_ALIGNMENT,
                    controls=[
                        IconButton(
                            icon=icons.KEYBOARD_ARROW_LEFT,
                            on_click=self.on_navigate_back,
                        ),
                        get_headline_txt(PROFILE, size=HEADLINE_4_SIZE),
                    ],
                ),
                Container(
                    self.progressBar,
                    margin=margin.symmetric(horizontal=dimens.SPACE_MD),
                ),
                self.profile_form,
            ],
        )
        view = Card(
            Container(
                padding=padding.all(dimens.SPACE_MD),
                content=self.form_container,
            ),
            width=dimens.MIN_WINDOW_WIDTH,
        )
        return view

    def will_unmount(self):
        self.mounted = False
