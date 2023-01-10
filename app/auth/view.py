from typing import Callable
from flet import (
    border_radius,
    Image,
    Column,
    Container,
    Row,
    UserControl,
    padding,
)
from core.abstractions import TuttleViewParams

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

from tuttle.model import User

from auth.intent import AuthIntent
from core.abstractions import ClientStorage, TuttleView
from core.utils import (
    CENTER_ALIGNMENT,
    KEYBOARD_EMAIL,
    KEYBOARD_NAME,
    KEYBOARD_NUMBER,
    KEYBOARD_PHONE,
    KEYBOARD_TEXT,
    START_ALIGNMENT,
    TXT_ALIGN_CENTER,
    is_empty_str,
    CONTAIN,
)
from core.models import IntentResult
from core import views
from res import dimens, colors, fonts, image_paths, res_utils

from .intent import AuthIntent


class LoginForm(UserControl):
    """Login form to set required user info"""

    def __init__(
        self,
        on_logged_in,
        on_save_user_callback,
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
        self.on_save_user = on_save_user_callback
        self.on_logged_in = on_logged_in

    def set_login_err(self, err: str = ""):
        self.login_err_txt.value = err
        self.login_err_txt.visible = err != ""

    def on_field_focus(self, e):
        for field in [
            self.name_field,
            self.email_field,
            self.phone_field,
            self.title_field,
        ]:
            field.error_text = ""
        self.set_login_err()
        if self.mounted:
            self.update()

    def on_change_value(self, form_property, e):
        setattr(self, form_property, e.control.value)

    def on_submit_btn_clicked(self, e):

        # prevent multiple clicking
        self.submit_btn.disabled = True

        # hide any errors
        self.login_err_txt.value = ""
        self.login_err_txt.visible = False
        self.form_error = ""

        missingRequiredDataErr = ""
        if is_empty_str(self.name):
            missingRequiredDataErr = "Your name is required."
            self.name_field.error_text = missingRequiredDataErr
        elif is_empty_str(self.email):
            missingRequiredDataErr = "Your email is required."
            self.email_field.error_text = missingRequiredDataErr
        elif is_empty_str(self.phone):
            missingRequiredDataErr = "Your phone number is required."
            self.phone_field.error_text = missingRequiredDataErr
        elif is_empty_str(self.title):
            missingRequiredDataErr = "Please specify your job title. e.g. freelancer"
            self.title_field.error_text = missingRequiredDataErr

        elif (
            is_empty_str(self.street)
            or is_empty_str(self.street_number)
            or is_empty_str(self.postal_code)
            or is_empty_str(self.country)
            or is_empty_str(self.city)
        ):

            missingRequiredDataErr = "Please provide your full address"
            self.set_login_err(missingRequiredDataErr)

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
                self.set_login_err(self.form_error)
                self.submit_btn.disabled = False
                self.update()
            else:
                # user is authenticated
                self.on_logged_in()
        else:
            self.submit_btn.disabled = False
            if self.mounted:
                self.update()

    def build(self):
        """Called when form is built"""
        self.name_field = views.get_std_txt_field(
            lambda e: self.on_change_value("name", e),
            "Name",
            "your name",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_NAME,
        )
        self.email_field = views.get_std_txt_field(
            lambda e: self.on_change_value("email", e),
            "Email",
            "your email address",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_EMAIL,
        )
        self.phone_field = views.get_std_txt_field(
            lambda e: self.on_change_value("phone", e),
            "Phone",
            "your phone number",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_PHONE,
        )
        self.title_field = views.get_std_txt_field(
            lambda e: self.on_change_value("title", e),
            "Job Title",
            "your work title",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_TEXT,
        )
        self.street_field = views.get_std_txt_field(
            lambda e: self.on_change_value("street", e),
            lbl="Street Name",
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.street_number_field = views.get_std_txt_field(
            lambda e: self.on_change_value("street_number", e),
            lbl="Street Number",
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )
        self.postal_code_field = views.get_std_txt_field(
            lambda e: self.on_change_value("postal_code", e),
            lbl="Postal Code",
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )

        self.city_field = views.get_std_txt_field(
            lambda e: self.on_change_value("city", e),
            lbl="City",
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.country_field = views.get_std_txt_field(
            lambda e: self.on_change_value("country", e),
            lbl="Country",
            keyboard_type=KEYBOARD_TEXT,
        )
        self.login_err_txt = views.get_error_txt(self.form_error)
        self.submit_btn = views.get_primary_btn(
            on_click=self.on_submit_btn_clicked,
            label="Get Started",
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
            ],
        )

        return self.form

    def did_mount(self):
        self.mounted = True

    def will_unmount(self):
        self.mounted = False


class SplashScreen(TuttleView, UserControl):
    def __init__(self, params: TuttleViewParams):
        super().__init__(params=params)
        self.keep_back_stack = False
        self.intent_handler = AuthIntent()

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
        self.navigate_to_route(res_utils.HOME_SCREEN_ROUTE)

    def check_auth_status(self):
        """checks if user is already created

        if created, re routes to home
        else shows login form
        """
        result = self.intent_handler.get_user()
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
            on_save_user_callback=self.on_save_user,
        )
        self.form_container.controls.remove(self.loading_indicator)
        self.form_container.controls.append(form)
        if self.mounted:
            self.update()

    def did_mount(self):
        try:
            self.mounted = True
            self.check_auth_status()
        except Exception as e:
            self.mounted = False
            print(f"exception raised @splash_screen.did_mount {e}")

    def build(self):
        """Called when page is built"""
        self.loading_indicator = views.horizontal_progress
        self.form_container = Column(
            controls=[
                views.get_labelled_logo(),
                views.get_headline_with_subtitle(
                    "Hi, Welcome to Tuttle.", "Let's get you started"
                ),
                self.loading_indicator,
                views.stdSpace,
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
                    padding=padding.all(dimens.SPACE_XS),
                    content=Column(
                        alignment=START_ALIGNMENT,
                        horizontal_alignment=CENTER_ALIGNMENT,
                        expand=True,
                        controls=[
                            views.mdSpace,
                            views.get_image(
                                image_paths.splashImgPath,
                                "welcome screen image",
                                width=300,
                            ),
                            views.get_headline_with_subtitle(
                                "Tuttle",
                                "Time and money management for freelancers",
                                alignmentInContainer=CENTER_ALIGNMENT,
                                txtAlignment=TXT_ALIGN_CENTER,
                                titleSize=fonts.HEADLINE_3_SIZE,
                                subtitleSize=fonts.HEADLINE_4_SIZE,
                            ),
                        ],
                    ),
                ),
                Container(
                    col={"xs": 12, "sm": 7},
                    padding=padding.all(dimens.SPACE_XL),
                    content=self.form_container,
                ),
            ],
        )
        return page_view

    def will_unmount(self):
        self.mounted = False


class ProfileScreen(TuttleView, UserControl):
    def __init__(self, params: TuttleViewParams):
        super().__init__(params=params)
        self.horizontal_alignment_in_parent = CENTER_ALIGNMENT
        self.intent_handler = AuthIntent()
        self.name = ""
        self.email = ""
        self.phone = ""
        self.title = ""
        self.street = ""
        self.street_number = ""
        self.postal_code = ""
        self.city = ""
        self.country = ""
        self.profile_pic_url = ""

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
        self.toggle_progress_bar()

        missingRequiredDataErr = ""
        if is_empty_str(self.name):
            missingRequiredDataErr = "Your name is required."
            self.name_field.error_text = missingRequiredDataErr
        elif is_empty_str(self.email):
            missingRequiredDataErr = "Your email address is required."
            self.email_field.error_text = missingRequiredDataErr
        elif is_empty_str(self.phone):
            missingRequiredDataErr = "Your phone number is required."
            self.phone_field.error_text = missingRequiredDataErr
        elif is_empty_str(self.title):
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
        self.toggle_progress_bar(hide_progress=True)

    def on_update_photo_clicked(self, e):
        self.pick_file_callback(
            on_file_picker_result=self.on_profile_photo_picked,
            on_upload_progress=self.on_upload_profile_pic_progress,
            allowed_extensions=["png", "jpeg", "jpg"],
            dialog_title="Tuttle profile photo",
            file_type="custom",
        )

    def on_profile_photo_picked(self, e):
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.toggle_progress_bar(f"Uploading file {file.name}")
            upload_url = self.upload_file_callback(file)
            if upload_url:
                self.uploaded_photo_url = upload_url

    def on_upload_profile_pic_progress(self, e):
        if e.progress == 1.0:
            self.toggle_progress_bar(f"Upload complete, processing file...")
            if self.uploaded_photo_url:
                result = self.intent_handler.update_user_photo(self.uploaded_photo_url)
                msg = "Failed to update photo"
                is_err = True
                if result.was_intent_successful:
                    self.profile_photo_control.src = self.uploaded_photo_url
                    msg = "Profile photo updated"
                    is_err = False
                self.show_snack(msg, is_err)
                self.uploaded_photo_url = None  # clear
            self.toggle_progress_bar(hide_progress=True)

    def toggle_progress_bar(self, msg: str = "", hide_progress: bool = False):
        self.progressBar.visible = not hide_progress
        self.update_btn.disabled = not hide_progress
        self.ongoing_action_hint.value = msg
        self.ongoing_action_hint.visible = msg != ""
        self.update()

    def refresh_user_info(self):
        if self.user is None:
            return
        self.name = self.user.name
        self.email = self.user.email
        self.phone = self.user.phone_number
        self.title = self.user.subtitle
        self.profile_pic_url = self.user.profile_photo
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

    def set_profile_form(self):
        self.profile_photo_control = Image(
            src=self.profile_pic_url
            if self.profile_pic_url
            else image_paths.default_avatar,
            width=72,
            height=72,
            border_radius=border_radius.all(36),
            fit=CONTAIN,
        )
        self.name_field = views.get_std_txt_field(
            self.on_change_name,
            "Name",
            "your name",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_NAME,
        )
        self.email_field = views.get_std_txt_field(
            self.on_change_email,
            "Email",
            "your email address",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_EMAIL,
        )
        self.phone_field = views.get_std_txt_field(
            self.on_change_phone,
            "Phone",
            "Your phone number",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_PHONE,
        )
        self.title_field = views.get_std_txt_field(
            self.on_change_title,
            "Title",
            "your work title",
            on_focus=self.on_field_focus,
            keyboard_type=KEYBOARD_TEXT,
        )
        self.street_field = views.get_std_txt_field(
            on_change=self.on_street_changed,
            lbl="Street Name",
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )
        self.street_number_field = views.get_std_txt_field(
            on_change=self.on_street_num_changed,
            lbl="Street Number",
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )
        self.postal_code_field = views.get_std_txt_field(
            on_change=self.on_postal_code_changed,
            lbl="Postal Code",
            keyboard_type=KEYBOARD_NUMBER,
            expand=1,
        )

        self.city_field = views.get_std_txt_field(
            on_change=self.on_city_changed,
            lbl="City",
            keyboard_type=KEYBOARD_TEXT,
            expand=1,
        )

        self.country_field = views.get_std_txt_field(
            on_change=self.on_country_changed,
            lbl="Country",
            keyboard_type=KEYBOARD_TEXT,
        )

        self.update_photo_btn = views.get_secondary_btn(
            label="Update photo", on_click=self.on_update_photo_clicked
        )
        self.update_btn = views.get_primary_btn(
            on_click=self.on_update_btn_clicked,
            label="Update Profile",
        )
        self.profile_form = Column(
            spacing=dimens.SPACE_MD,
            controls=[
                self.profile_photo_control,
                self.update_photo_btn,
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

    def build(self):
        self.progressBar = views.horizontal_progress
        self.progressBar.visible = False
        self.ongoing_action_hint = views.get_body_txt(txt="")
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
                        views.get_headline_txt("Profile", size=fonts.HEADLINE_4_SIZE),
                    ],
                ),
                Container(
                    self.progressBar,
                    margin=margin.symmetric(horizontal=dimens.SPACE_MD),
                ),
                self.ongoing_action_hint,
                self.profile_form,
            ],
        )
        view = Card(
            Container(
                padding=padding.all(dimens.SPACE_MD),
                margin=margin.symmetric(vertical=dimens.SPACE_LG),
                content=self.form_container,
            ),
            width=dimens.MIN_WINDOW_WIDTH,
        )
        return view

    def did_mount(self):
        try:
            self.mounted = True
            self.toggle_progress_bar()
            result: IntentResult = self.intent_handler.get_user()
            if not result.was_intent_successful:
                self.show_snack(result.error_msg, True)
            else:
                self.user: User = result.data
                self.refresh_user_info()
            self.toggle_progress_bar(hide_progress=True)
        except Exception as e:
            # log error
            print(f"exception raised @profile_screen.did_mount {e}")

    def will_unmount(self):
        self.mounted = False
