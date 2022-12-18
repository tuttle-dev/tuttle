from typing import Callable

from flet import Column, Container, Row, UserControl, padding

from typing import Callable

from flet import (
    Card,
    Column,
    Container,
    IconButton,
    ResponsiveRow,
    Row,
    UserControl,
    icons,
    margin,
    padding,
)

from auth.intent import AuthIntent
from auth.model import User
from core.abstractions import ClientStorage, TuttleView
from core.constants_and_enums import (
    CENTER_ALIGNMENT,
    KEYBOARD_EMAIL,
    KEYBOARD_NAME,
    KEYBOARD_NUMBER,
    KEYBOARD_PHONE,
    KEYBOARD_TEXT,
    START_ALIGNMENT,
    TXT_ALIGN_CENTER,
)
from core.models import IntentResult
from core.views import (
    get_error_txt,
    get_headline_txt,
    get_headline_with_subtitle,
    get_image,
    get_labelled_logo,
    get_primary_btn,
    get_std_txt_field,
    get_secondary_btn,
    horizontal_progress,
    mdSpace,
    stdSpace,
)
from res import dimens
from res.dimens import SPACE_XL, SPACE_XS
from res.fonts import HEADLINE_3_SIZE, HEADLINE_4_SIZE
from res.image_paths import splashImgPath
from res.utils import HOME_SCREEN_ROUTE

from .intent import AuthIntent


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

    def on_submit_btn_clicked(self, e):
        # prevent multiple clicking
        self.submit_btn.disabled = True

        # hide any errors
        self.login_err_txt.visible = False
        self.form_error = ""

        missingRequiredDataErr = ""
        if len(self.name.strip()) == 0:
            missingRequiredDataErr = "Your name is required."
            self.name_field.error_text = missingRequiredDataErr
        elif len(self.email.strip()) == 0:
            missingRequiredDataErr = "Your email is required."
            self.email_field.error_text = missingRequiredDataErr
        elif len(self.phone.strip()) == 0:
            missingRequiredDataErr = "Your phone number is required."
            self.phone_field.error_text = missingRequiredDataErr
        elif len(self.title.strip()) == 0:
            missingRequiredDataErr = "Please specify a title. e.g. freelancer"
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
            if self.mounted:
                self.update()

    def on_skip_clicked(self, e):
        self.on_logged_in()

    def build(self):
        """Called when form is built"""
        self.name_field = get_std_txt_field(
            self.on_change_name,
            "Name",
            "your name",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_NAME,
        )
        self.email_field = get_std_txt_field(
            self.on_change_email,
            "Email",
            "your email address",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_EMAIL,
        )
        self.phone_field = get_std_txt_field(
            self.on_change_phone,
            "Phone",
            "your phone number",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_PHONE,
        )
        self.title_field = get_std_txt_field(
            self.on_change_title,
            "Title",
            "your work title",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_TEXT,
        )
        self.street_field = get_std_txt_field(
            on_change=self.on_street_changed,
            lbl="Street Name",
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.street_number_field = get_std_txt_field(
            on_change=self.on_street_num_changed,
            lbl="Street Number",
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )
        self.postal_code_field = get_std_txt_field(
            on_change=self.on_postal_code_changed,
            lbl="Postal Code",
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )

        self.city_field = get_std_txt_field(
            on_change=self.on_city_changed,
            lbl="City",
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.country_field = get_std_txt_field(
            on_change=self.on_country_changed,
            lbl="Country",
            keyboard_type=KEYBOARD_TEXT,
        )
        self.login_err_txt = get_error_txt(self.form_error)
        self.submit_btn = get_primary_btn(
            on_click=self.on_submit_btn_clicked,
            label="Get Started",
        )
        self.skip_btn = get_secondary_btn(
            on_click=self.on_skip_clicked,
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
                self.skip_btn,
            ],
        )

        return self.form

    def did_mount(self):
        self.mounted = True

    def will_unmount(self):
        self.mounted = False


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
        self.intent_handler = AuthIntent(local_storage=local_storage)
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
            missingRequiredDataErr = "Your name is required."
            self.name_field.error_text = missingRequiredDataErr
        elif len(self.email.strip()) == 0:
            missingRequiredDataErr = "Your email address is required."
            self.email_field.error_text = missingRequiredDataErr
        elif len(self.phone.strip()) == 0:
            missingRequiredDataErr = "Your phone number is required."
            self.phone_field.error_text = missingRequiredDataErr
        elif len(self.title.strip()) == 0:
            missingRequiredDataErr = "Please specify your title. e.g. freelancer"
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
                self.show_snack("Your profile has been updated", False)
                self.user: User = result.data
                self.refresh_user_info()
        self.update_btn.disabled = False
        self.progressBar.visible = False
        self.update()

    def set_profile_form(self):
        self.name_field = get_std_txt_field(
            self.on_change_name,
            "Name",
            "your name",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_NAME,
        )
        self.email_field = get_std_txt_field(
            self.on_change_email,
            "Email",
            "your email address",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_EMAIL,
        )
        self.phone_field = get_std_txt_field(
            self.on_change_phone,
            "Phone",
            "Your phone number",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_PHONE,
        )
        self.title_field = get_std_txt_field(
            self.on_change_title,
            "Title",
            "your work title",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_TEXT,
        )
        self.street_field = get_std_txt_field(
            on_change=self.on_street_changed,
            lbl="Street Name",
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.street_number_field = get_std_txt_field(
            on_change=self.on_street_num_changed,
            lbl="Street Number",
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )
        self.postal_code_field = get_std_txt_field(
            on_change=self.on_postal_code_changed,
            lbl="Postal Code",
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )

        self.city_field = get_std_txt_field(
            on_change=self.on_city_changed,
            lbl="City",
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )

        self.country_field = get_std_txt_field(
            on_change=self.on_country_changed,
            lbl="Country",
            keyboard_type=KEYBOARD_TEXT,
        )

        self.update_btn = get_primary_btn(
            on_click=self.on_update_btn_clicked,
            label="Update Profile",
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
                        get_headline_txt("Profile", size=HEADLINE_4_SIZE),
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


class SplashView(UserControl):
    def build(self):
        view = Column(
            alignment=START_ALIGNMENT,
            horizontal_alignment=CENTER_ALIGNMENT,
            expand=True,
            controls=[
                mdSpace,
                get_image(splashImgPath, "welcome screen image", width=300),
                get_headline_with_subtitle(
                    "Tuttle",
                    "Time and money management for freelancers",
                    alignmentInContainer=CENTER_ALIGNMENT,
                    txtAlignment=TXT_ALIGN_CENTER,
                    titleSize=HEADLINE_3_SIZE,
                    subtitleSize=HEADLINE_4_SIZE,
                ),
            ],
        )

        return view


class SplashScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route: Callable,
        show_snack: Callable,
        dialog_controller: Callable,
        local_storage: ClientStorage,
    ):
        super().__init__(
            navigate_to_route,
            show_snack,
            dialog_controller,
            keep_back_stack=False,
        )
        self.intent_handler = AuthIntent(local_storage=local_storage)

    def on_save_user(
        self,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        street_num: str,
        postal_code: str,
        city: str,
        country: str,
    ):
        return self.intent_handler.create_user(
            title=title,
            name=name,
            email=email,
            phone=phone,
            street=street,
            street_num=street_num,
            postal_code=postal_code,
            city=city,
            country=country,
        )

    def on_logged_in(self):
        self.navigate_to_route(HOME_SCREEN_ROUTE)

    def check_auth_status(self):
        """checks if user is already created

        if created, re routes to home
        else shows login form
        """
        result = self.intent_handler.get_user_test_login()
        if result.was_intent_successful:
            if result.data is not None:
                self.on_logged_in()
            else:
                self.show_login_form()
        else:
            self.show_snack(result.error_msg)

    def show_login_form(self):
        form = LoginForm(
            on_logged_in=self.on_logged_in,
            on_save_user=self.on_save_user,
        )
        self.form_container.controls.remove(self.loading_indicator)
        self.form_container.controls.append(form)
        if self.mounted:
            self.update()

    def did_mount(self):
        try:
            self.mounted = True
            self.check_auth_status()
            # uncomment to skip login screen self.on_logged_in()
        except Exception as e:
            # log
            self.mounted = False
            print(f"exception raised @splash_screen.did_mount {e}")

    def build(self):
        """Called when page is built"""
        self.loading_indicator = horizontal_progress
        self.form_container = Column(
            controls=[
                get_labelled_logo(),
                get_headline_with_subtitle(
                    "Hi, Welcome to Tuttle.", "Let's get you started"
                ),
                self.loading_indicator,
                stdSpace,
            ]
        )
        page_view = ResponsiveRow(
            spacing=0,
            run_spacing=0,
            alignment=CENTER_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[
                Container(
                    col={"xs": 12, "sm": 5},
                    padding=padding.all(SPACE_XS),
                    content=SplashView(),
                ),
                Container(
                    col={"xs": 12, "sm": 7},
                    padding=padding.all(SPACE_XL),
                    content=self.form_container,
                ),
            ],
        )
        return page_view

    def will_unmount(self):
        self.mounted = False