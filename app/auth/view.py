from flet import (
    Column,
    Container,
    Row,
    UserControl,
    Card,
    IconButton,
    ResponsiveRow,
    icons,
    margin,
    padding,
)
from core.abstractions import TuttleViewParams
from typing import Callable
from tuttle.model import User

from auth.intent import AuthIntent
from core.abstractions import TuttleView
from core import views, utils
from core.intent_result import IntentResult
from res import dimens, fonts, image_paths, res_utils

from .intent import AuthIntent


class UserDataForm(UserControl):
    """Form view for setting the user info"""

    def __init__(
        self,
        on_submit_success: Callable,
        on_form_submit: Callable,
        submit_btn_label: Callable,
    ):
        super().__init__()
        """
        Parameters
        ----------
        on_submit_success : Callable
            Callback function to handle when the form submission is succesful
        on_form_submit : Callable
            Callback function to handle when the form's submit button  is clicked
        submit_btn_label : str
            The label to display on the submit button
        """
        self.name = ""
        self.email = ""
        self.phone = ""
        self.title = ""
        self.street = ""
        self.street_number = ""
        self.postal_code = ""
        self.city = ""
        self.country = ""
        self.on_form_submit = on_form_submit
        self.on_submit_success = on_submit_success
        self.submit_btn_label = submit_btn_label

    def toggle_form_err(self, error: str = ""):
        """hides or displays the form error

        *a form error is not tied to a single specific field
        """
        self.form_err_control.value = error
        self.form_err_control.visible = error != ""
        self.update()

    def on_field_focus(self, e):
        for field in [
            self.name_field,
            self.email_field,
            self.phone_field,
            self.title_field,
        ]:
            field.error_text = ""
        self.toggle_form_err()
        self.update()

    def on_field_value_changed(self, form_property, e):
        """updates the property corresponding to this form field"""
        setattr(self, form_property, e.control.value)

    def on_submit_btn_clicked(self, e):
        # prevent multiple clicking
        self.submit_btn.disabled = True

        # hide any errors
        self.toggle_form_err()

        missing_required_data_err = ""
        if utils.is_empty_str(self.name):
            missing_required_data_err = "Your name is required."
            self.name_field.error_text = missing_required_data_err
        elif utils.is_empty_str(self.email):
            missing_required_data_err = "Your email is required."
            self.email_field.error_text = missing_required_data_err
        elif utils.is_empty_str(self.phone):
            missing_required_data_err = "Your phone number is required."
            self.phone_field.error_text = missing_required_data_err
        elif utils.is_empty_str(self.title):
            missing_required_data_err = "Please specify your job title. e.g. freelancer"
            self.title_field.error_text = missing_required_data_err

        elif (
            utils.is_empty_str(self.street)
            or utils.is_empty_str(self.street_number)
            or utils.is_empty_str(self.postal_code)
            or utils.is_empty_str(self.country)
            or utils.is_empty_str(self.city)
        ):

            missing_required_data_err = "Please provide your full address"
            self.toggle_form_err(missing_required_data_err)

        if not missing_required_data_err:
            # save user
            result: IntentResult = self.on_form_submit(
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
                self.toggle_form_err(result.error_msg)
                self.update()
            else:
                # user is authenticated
                self.on_submit_success(result.data)
        self.submit_btn.disabled = False
        self.update()

    def build(self):
        """Called when form is built"""
        self.name_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("name", e),
            "Name",
            "your name",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_NAME,
        )
        self.email_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("email", e),
            "Email",
            "your email address",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_EMAIL,
        )
        self.phone_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("phone", e),
            "Phone",
            "your phone number",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_PHONE,
        )
        self.title_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("title", e),
            "Job Title",
            "your work title",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_TEXT,
        )
        self.street_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("street", e),
            label="Street Name",
            keyboard_type=utils.KEYBOARD_TEXT,
            expand=1,
        )
        self.street_number_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("street_number", e),
            label="Street Number",
            keyboard_type=utils.KEYBOARD_NUMBER,
            expand=1,
        )
        self.postal_code_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("postal_code", e),
            label="Postal Code",
            keyboard_type=utils.KEYBOARD_NUMBER,
            expand=1,
        )

        self.city_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("city", e),
            label="City",
            keyboard_type=utils.KEYBOARD_TEXT,
            expand=1,
        )
        self.country_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("country", e),
            label="Country",
            keyboard_type=utils.KEYBOARD_TEXT,
        )
        self.form_err_control = views.get_error_txt("")
        self.submit_btn = views.get_primary_btn(
            on_click=self.on_submit_btn_clicked,
            label=self.submit_btn_label,
        )
        return Column(
            spacing=dimens.SPACE_MD,
            controls=[
                self.title_field,
                self.name_field,
                self.email_field,
                self.phone_field,
                Row(
                    vertical_alignment=utils.CENTER_ALIGNMENT,
                    controls=[
                        self.street_field,
                        self.street_number_field,
                    ],
                ),
                Row(
                    vertical_alignment=utils.CENTER_ALIGNMENT,
                    controls=[
                        self.postal_code_field,
                        self.city_field,
                    ],
                ),
                self.country_field,
                self.form_err_control,
                self.submit_btn,
            ],
        )

    def refresh_user_info(self, user: User):
        if user is None:
            return
        self.name_field.value = self.name = user.name
        self.email_field.value = self.email = user.email
        self.phone_field.value = self.phone = user.phone_number
        self.title_field.value = self.title = user.subtitle
        self.street_field.value = self.street = user.address.street
        self.postal_code_field.value = self.postal_code = user.address.postal_code
        self.street_number_field.value = self.street_number = user.address.number
        self.city_field.value = self.city = user.address.city
        self.country_field.value = self.country = user.address.country
        self.update()


class SplashScreen(TuttleView, UserControl):
    """Displayed the first time the app loads

    Checks if user has been created
    If created, redirects user to the homepage
    If not created, displays a create user form
    """

    def __init__(
        self,
        params: TuttleViewParams,
        install_demo_data_callback,
    ):
        super().__init__(params=params)
        self.keep_back_stack = False  # User cannot go back from this screen
        self.intent = AuthIntent()
        self.install_demo_data_callback = install_demo_data_callback

    def show_login_if_signed_out_else_redirect(self):
        result = self.intent.get_user_if_exists_intent()
        if result.was_intent_successful:
            if result.data is not None:
                self.navigate_to_route(res_utils.HOME_SCREEN_ROUTE)
            else:
                self.set_login_form()
        else:
            self.show_snack(result.error_msg)

    def set_login_form(self):
        form = UserDataForm(
            on_submit_success=lambda _: self.navigate_to_route(
                res_utils.HOME_SCREEN_ROUTE
            ),
            on_form_submit=lambda title, name, email, phone, street, street_num, postal_code, city, country: self.intent.create_user_intent(
                title=title,
                name=name,
                email=email,
                phone=phone,
                street=street,
                street_num=street_num,
                postal_code=postal_code,
                city=city,
                country=country,
            ),
            submit_btn_label="Save Profile",
        )
        self.form_container.controls.remove(self.loading_indicator)
        self.form_container.controls.append(form)
        self.update_self()

    def on_proceed_with_demo_data_clicked(self, e):
        self.install_demo_data_callback()
        self.navigate_to_route(res_utils.HOME_SCREEN_ROUTE)

    def did_mount(self):
        self.mounted = True
        self.show_login_if_signed_out_else_redirect()

    def build(self):
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
            alignment=utils.CENTER_ALIGNMENT,
            vertical_alignment=utils.CENTER_ALIGNMENT,
            controls=[
                Container(
                    col={"xs": 12, "sm": 5},
                    padding=padding.all(dimens.SPACE_XS),
                    content=Column(
                        alignment=utils.START_ALIGNMENT,
                        horizontal_alignment=utils.CENTER_ALIGNMENT,
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
                                alignment_in_container=utils.CENTER_ALIGNMENT,
                                txtAlignment=utils.TXT_ALIGN_CENTER,
                                titleSize=fonts.HEADLINE_3_SIZE,
                                subtitleSize=fonts.HEADLINE_4_SIZE,
                            ),
                        ],
                    ),
                ),
                Container(
                    col={"xs": 12, "sm": 7},
                    padding=padding.all(dimens.SPACE_XL),
                    content=Column(
                        [
                            self.form_container,
                            views.get_secondary_btn(
                                on_click=self.on_proceed_with_demo_data_clicked,
                                label="Proceed with demo data",
                            ),
                        ]
                    ),
                ),
            ],
        )
        return page_view

    def will_unmount(self):
        self.mounted = False


class ProfileScreen(TuttleView, UserControl):
    """User profile screen

    Displays a UserDataForm for updating user profile
    Displays the User's photo if set and provides a way to update it
    """

    def __init__(self, params: TuttleViewParams):
        super().__init__(params=params)
        self.horizontal_alignment_in_parent = utils.CENTER_ALIGNMENT
        self.intent = AuthIntent()
        self.uploaded_photo_path = ""
        self.user_profile: User = None

    def on_profile_updated(self, data):
        self.show_snack("Your profile has been updated", False)
        self.user_profile: User = data

    def on_update_photo_clicked(self, e):
        self.pick_file_callback(
            on_file_picker_result=self.on_profile_photo_picked,
            on_upload_progress=self.uploading_profile_pic_progress_listener,
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
                self.uploaded_photo_path = upload_url

    def uploading_profile_pic_progress_listener(self, e):
        if e.progress == 1.0:
            self.toggle_progress_bar(f"Upload complete, processing file...")
            if self.uploaded_photo_path:
                result = self.intent.update_user_photo_path_intent(
                    self.user_profile,
                    self.uploaded_photo_path,
                )
                # assume error occurred
                msg = result.error_msg
                is_err = True
                if result.was_intent_successful:
                    self.profile_photo_control.src = self.uploaded_photo_path
                    msg = "Profile photo updated"
                    is_err = False
                self.show_snack(msg, is_err)
                if is_err:
                    self.user_profile.profile_photo_path = ""
                self.uploaded_photo_path = None  # clear
            self.toggle_progress_bar(hide_progress=True)

    def toggle_progress_bar(self, msg: str = "", hide_progress: bool = False):
        self.progressBar.visible = not hide_progress
        self.ongoing_action_hint.value = msg
        self.ongoing_action_hint.visible = msg != ""
        self.update_self()

    def build(self):
        self.progressBar = views.horizontal_progress
        self.progressBar.visible = False
        self.ongoing_action_hint = views.get_body_txt(txt="")
        self.profile_photo_control = views.get_profile_photo_img()
        self.update_photo_btn = views.get_secondary_btn(
            label="Update photo", on_click=self.on_update_photo_clicked
        )
        self.user_data_form = UserDataForm(
            on_form_submit=lambda title, name, email, phone, street, street_num, postal_code, city, country: self.intent.update_user_intent(
                title=title,
                name=name,
                email=email,
                phone=phone,
                street=street,
                street_num=street_num,
                postal_code=postal_code,
                city=city,
                country=country,
                user=self.user_profile,
            ),
            on_submit_success=self.on_profile_updated,
            submit_btn_label="Update Profile",
        )

        return Card(
            Container(
                padding=padding.all(dimens.SPACE_MD),
                margin=margin.symmetric(vertical=dimens.SPACE_LG),
                content=Column(
                    spacing=dimens.SPACE_STD,
                    run_spacing=0,
                    controls=[
                        Row(
                            spacing=dimens.SPACE_STD,
                            run_spacing=0,
                            vertical_alignment=utils.CENTER_ALIGNMENT,
                            controls=[
                                IconButton(
                                    icon=icons.KEYBOARD_ARROW_LEFT,
                                    on_click=self.on_navigate_back,
                                ),
                                views.get_headline_txt(
                                    "Profile", size=fonts.HEADLINE_4_SIZE
                                ),
                            ],
                        ),
                        Container(
                            self.progressBar,
                            margin=margin.symmetric(horizontal=dimens.SPACE_MD),
                        ),
                        self.ongoing_action_hint,
                        Column(
                            spacing=dimens.SPACE_MD,
                            controls=[
                                self.profile_photo_control,
                                self.update_photo_btn,
                                self.user_data_form,
                            ],
                        ),
                    ],
                ),
            ),
            width=dimens.MIN_WINDOW_WIDTH,
        )

    def did_mount(self):
        self.mounted = True
        self.toggle_progress_bar()
        result: IntentResult = self.intent.get_user_if_exists_intent()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.user_profile: User = result.data
            self.user_data_form.refresh_user_info(self.user_profile)
            if self.user_profile.profile_photo_path:
                self.profile_photo_control.src = self.user_profile.profile_photo_path
        self.toggle_progress_bar(hide_progress=True)

    def will_unmount(self):
        self.mounted = False
