from typing import Callable, Optional

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
from core import utils, views
from core.abstractions import TuttleView, TuttleViewParams
from core.intent_result import IntentResult
from res import dimens, fonts, image_paths, res_utils

from tuttle.model import User, BankAccount

from .intent import AuthIntent


class PaymentDataForm(UserControl):
    """Form view for setting the user's payment info"""

    def __init__(
        self,
        on_form_submit: Callable[[User], None],
        user: User,
    ):
        super().__init__()
        self.on_form_submit = on_form_submit
        self.user = user
        self.set_form_data()

    def set_form_data(self):
        """Sets the form data to the user's current data"""
        if not self.user.bank_account:
            # Create a new bank account if none exists
            self.user.bank_account = BankAccount(name="", BIC="", IBAN="")
        self.bank_bic = self.user.bank_account.BIC
        self.bank_name = self.user.bank_account.name
        self.bank_iban = self.user.bank_account.IBAN
        self.vat_number = self.user.VAT_number

    def update_form_data(self, user: User):
        """Updates the user's data with the form data"""
        self.user = user
        self.set_form_data()
        self.update()

    def on_vat_number_changed(self, e):
        """Called when the VAT number field is changed"""
        self.vat_number = e.control.value
        self.user.VAT_number = self.vat_number

    def on_bank_bic_changed(self, e):
        """Called when the bank BIC field is changed"""
        self.bank_bic = e.control.value
        self.user.bank_account.BIC = self.bank_bic

    def on_bank_iban_changed(self, e):
        """Called when the bank IBAN field is changed"""
        self.bank_iban = e.control.value
        self.user.bank_account.IBAN = self.bank_iban

    def on_bank_name_changed(self, e):
        """Called when the bank name field is changed"""
        self.bank_name = e.control.value
        self.user.bank_account.name = self.bank_name

    def build(self):
        """Called when form is built"""
        return Column(
            spacing=dimens.SPACE_MD,
            controls=[
                views.get_std_txt_field(
                    on_change=self.on_vat_number_changed,
                    label="VAT Number",
                    hint="Value Added Tax number of the user, legally required for invoices.",
                    initial_value=self.vat_number,
                ),
                views.xsSpace,
                views.get_sub_heading_txt("Bank Account"),
                views.get_std_txt_field(
                    on_change=self.on_bank_name_changed,
                    label="Name",
                    initial_value=self.bank_name,
                ),
                views.get_std_txt_field(
                    on_change=self.on_bank_iban_changed,
                    label="IBAN",
                    initial_value=self.bank_iban,
                ),
                views.get_std_txt_field(
                    on_change=self.on_bank_bic_changed,
                    label="BIC",
                    initial_value=self.bank_bic,
                ),
                views.stdSpace,
                views.get_primary_btn(
                    label="Save",
                    on_click=lambda e: self.on_form_submit(self.user),
                ),
            ],
        )


class UserDataForm(UserControl):
    """Form view for setting the user info"""

    def __init__(
        self,
        on_submit_success: Callable,
        on_form_submit: Callable,
        submit_btn_label: str,
    ):
        super().__init__()
        """
        Parameters
        ----------
        on_submit_success : Callable
            Callback function to handle when the form submission is successful
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
        self.website = ""
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
                website=self.website,
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
            "Phone (optional)",
            "your phone number",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_PHONE,
        )
        self.title_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("title", e),
            "Job Title",
            "What is your role as a freelancer?",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_TEXT,
        )
        self.website_field = views.get_std_txt_field(
            lambda e: self.on_field_value_changed("website", e),
            "Website (optional)",
            "URL of your website.",
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
                self.website_field,
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
        self.website_field.value = self.website = user.website
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
        self.client_storage = params.client_storage

    def show_login_if_signed_out_else_redirect(self):
        result = self.intent.get_user_if_exists()
        if result.was_intent_successful:
            if result.data is not None:
                self.navigate_to_route(res_utils.HOME_SCREEN_ROUTE)
            else:
                # clear preferences if any
                self.client_storage.clear_preferences()
                self.set_login_form()
        else:
            self.show_snack(result.error_msg)

    def set_login_form(self):
        form = UserDataForm(
            on_submit_success=lambda _: self.navigate_to_route(
                res_utils.HOME_SCREEN_ROUTE
            ),
            on_form_submit=lambda title, name, email, phone, street, street_num, postal_code, city, country, website: self.intent.create_user(
                title=title,
                name=name,
                email=email,
                phone=phone,
                street=street,
                street_num=street_num,
                postal_code=postal_code,
                city=city,
                country=country,
                website=website,
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
                # views.get_labelled_logo(),
                views.get_heading_with_subheading(
                    "Welcome to Tuttle",
                    "Let's get you started: Please enter your details below. Your data will be stored locally and will not be sent to a server.",
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
                            views.get_heading_with_subheading(
                                "Tuttle",
                                "Time and money management for freelancers",
                                alignment_in_container=utils.CENTER_ALIGNMENT,
                                txt_alignment=utils.TXT_ALIGN_CENTER,
                                title_size=fonts.HEADLINE_3_SIZE,
                                subtitle_size=fonts.HEADLINE_4_SIZE,
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
                                label="Proceed with demo",
                                icon="TOYS",
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
    Displays the User's payment information if set and provides a way to update it
    """

    def __init__(self, params: TuttleViewParams):
        super().__init__(params=params)
        self.intent = AuthIntent()
        self.uploaded_photo_path = ""
        self.user_profile: User = None

    def refresh_payment_section(self):
        """Refreshes the payment section of the profile screen"""
        self.payment_data_form = PaymentDataForm(
            on_form_submit=self.on_update_user_invoice_data,
            user=self.user_profile,
        )
        self.payment_info_controls.append(self.payment_data_form)

    def on_update_user_invoice_data(self, user: User):
        """Callback for when user updates their payment information"""
        result: IntentResult = self.intent.update_user(user)
        if result.was_intent_successful:
            self.show_snack("Payment information updated successfully")
            self.user_profile = result.data
            self.payment_data_form.update_form_data(user=self.user_profile)
        else:
            self.show_snack(result.error_msg, is_error=True)

    def on_profile_updated(self, data):
        """Callback for when user profile has been updated successfully"""
        self.show_snack("Your profile has been updated")
        self.user_profile: User = data

    def on_update_photo_clicked(self, e):
        """Callback for when user clicks on the update photo button"""
        self.pick_file_callback(
            on_file_picker_result=self.on_profile_photo_picked,
            on_upload_progress=self.uploading_profile_pic_progress_listener,
            allowed_extensions=["png", "jpeg", "jpg"],
            dialog_title="Tuttle profile photo",
            file_type="custom",
        )

    def on_profile_photo_picked(self, e):
        """Callback for when profile photo has been picked"""
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.toggle_progress_bar(f"Uploading file {file.name}")
            upload_url = self.upload_file_callback(file)
            if upload_url:
                self.uploaded_photo_path = upload_url

    def uploading_profile_pic_progress_listener(self, e):
        """Callback for when profile photo is being uploaded"""
        if e.progress == 1.0:
            self.toggle_progress_bar(f"Upload complete, processing file...")
            if self.uploaded_photo_path:
                result = self.intent.update_user_photo_path(
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
        """Toggles the progress bar and the ongoing action hint"""
        self.progressBar.visible = not hide_progress
        self.ongoing_action_hint.value = msg
        self.ongoing_action_hint.visible = msg != ""
        self.update_self()

    def build(self):
        """Builds the profile screen"""
        self.progressBar = views.horizontal_progress
        self.progressBar.visible = False
        self.ongoing_action_hint = views.get_body_txt(txt="")
        self.profile_photo_control = views.get_profile_photo_img()
        self.update_photo_btn = views.get_secondary_btn(
            label="Update profile picture", on_click=self.on_update_photo_clicked
        )
        self.user_data_form = UserDataForm(
            on_form_submit=lambda title, name, email, phone, street, street_num, postal_code, city, country, website: self.intent.update_user_with_info(
                title=title,
                name=name,
                email=email,
                phone=phone,
                street=street,
                street_num=street_num,
                postal_code=postal_code,
                city=city,
                country=country,
                website=website,
                user=self.user_profile,
            ),
            on_submit_success=self.on_profile_updated,
            submit_btn_label="Update Profile",
        )

        self.payment_info_controls = [
            views.get_heading(
                "Payment Settings",
                size=fonts.HEADLINE_4_SIZE,
            ),
        ]

        return ResponsiveRow(
            spacing=0,
            run_spacing=0,
            alignment=utils.START_ALIGNMENT,
            vertical_alignment=utils.START_ALIGNMENT,
            controls=[
                self.view_section(
                    [
                        Row(
                            spacing=dimens.SPACE_STD,
                            run_spacing=0,
                            vertical_alignment=utils.CENTER_ALIGNMENT,
                            controls=[
                                IconButton(
                                    icon=icons.KEYBOARD_ARROW_LEFT,
                                    on_click=self.on_navigate_back,
                                    icon_size=dimens.ICON_SIZE,
                                ),
                                views.get_heading(
                                    "Profile", size=fonts.HEADLINE_4_SIZE
                                ),
                            ],
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
                    ]
                ),
                self.view_section(self.payment_info_controls),
            ],
        )

    def view_section(self, controls: list[UserControl]) -> Card:
        """Returns a Card with the controls set to the contents of the card"""
        return Card(
            margin=margin.all(dimens.SPACE_LG),
            col={"xs": 12, "md": 6},
            content=Container(
                padding=padding.all(dimens.SPACE_MD),
                margin=margin.symmetric(vertical=dimens.SPACE_LG),
                content=Column(
                    spacing=dimens.SPACE_STD,
                    run_spacing=0,
                    controls=controls,
                ),
            ),
        )

    def did_mount(self):
        """Called when the view is mounted on page"""
        self.mounted = True
        self.toggle_progress_bar()
        result: IntentResult = self.intent.get_user_if_exists()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.user_profile: User = result.data
            # refresh user data form
            self.user_data_form.refresh_user_info(self.user_profile)
            if self.user_profile.profile_photo_path:
                self.profile_photo_control.src = self.user_profile.profile_photo_path
            # refresh invoice data form
            self.refresh_payment_section()
        self.toggle_progress_bar(hide_progress=True)

    def will_unmount(self):
        self.mounted = False
