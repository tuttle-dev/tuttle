from typing import Callable, Optional

from flet import (
    Column,
    Container,
    alignment,
    IconButton,
    icons,
    border,
    ResponsiveRow,
    Row,
    UserControl,
    padding,
    NavigationRailDestination,
    Icon,
)

from auth.intent import AuthIntent
from core import utils, views
from core.abstractions import TView, TViewParams
from core.intent_result import IntentResult
from res import dimens, fonts, image_paths, res_utils, colors, theme
from preferences.intent import PreferencesIntent
from tuttle.model import User, BankAccount

from .intent import AuthIntent


class PaymentDataForm(UserControl):
    """Form view for setting the user's payment info"""

    def __init__(
        self,
        on_form_submit: Callable[[User], None],
    ):
        super().__init__()
        self.on_form_submit = on_form_submit
        self.user: User = None

    def set_form_data(self):
        """Sets the form data to the user's current data"""
        if not self.user.bank_account:
            # Create a new bank account if none exists
            self.user.bank_account = BankAccount(name="", BIC="", IBAN="")
        self.bank_bic_field.value = self.user.bank_account.BIC
        self.bank_name_field.value = self.user.bank_account.name
        self.bank_iban_field.value = self.user.bank_account.IBAN
        self.vat_number_field.value = self.user.VAT_number

    def update_form_data(self, user: User):
        """Updates the user's data with the form data"""
        self.user = user
        self.set_form_data()
        self.update()

    def on_click_save(self, e):
        """Called when the save button is clicked"""
        self.user.VAT_number = self.vat_number_field.value
        self.user.bank_account.BIC = self.bank_bic_field.value
        self.user.bank_account.IBAN = self.bank_iban_field.value
        self.user.bank_account.name = self.bank_name_field.value
        self.on_form_submit(self.user)

    def build(self):
        """Called when form is built"""
        self.vat_number_field = views.TTextField(
            label="VAT Number",
            hint="Value Added Tax number of the user, legally required for invoices.",
        )
        self.bank_name_field = views.TTextField(
            label="Name",
            hint="Name of account",
        )
        self.bank_iban_field = views.TTextField(
            label="IBAN",
            hint="International Bank Account Number",
        )
        self.bank_bic_field = views.TTextField(
            label="BIC",
            hint="Bank Identifier Code",
        )
        return Column(
            spacing=dimens.SPACE_MD,
            controls=[
                self.vat_number_field,
                views.Spacer(xs_space=True),
                views.TSubHeading("Bank Account"),
                self.bank_name_field,
                self.bank_iban_field,
                self.bank_bic_field,
                views.Spacer(),
                views.TPrimaryButton(
                    label="Save",
                    on_click=self.on_click_save,
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
            self.subtitle_field,
        ]:
            field.error_text = ""
        self.toggle_form_err()
        self.update()

    def on_submit_btn_clicked(self, e):
        # prevent multiple clicking
        self.submit_btn.disabled = True

        # hide any errors
        self.toggle_form_err()

        missing_required_data_err = ""

        # get the form data
        subtitle = self.subtitle_field.value
        name = self.name_field.value
        email = self.email_field.value
        phone_number = self.phone_field.value
        address_street = self.street_field.value
        address_postal_code = self.postal_code_field.value
        address_number = self.street_number_field.value
        address_city = self.city_field.value
        address_country = self.country_field.value
        website = self.website_field.value

        # validate the form data
        if utils.is_empty_str(subtitle):
            missing_required_data_err = "Please specify your job title. e.g. freelancer"
            self.subtitle_field.error_text = missing_required_data_err

        elif utils.is_empty_str(name):
            missing_required_data_err = "Your name is required."
            self.name_field.error_text = missing_required_data_err

        elif utils.is_empty_str(email):
            missing_required_data_err = "Your email is required."
            self.email_field.error_text = missing_required_data_err

        elif (
            utils.is_empty_str(address_street)
            or utils.is_empty_str(address_number)
            or utils.is_empty_str(address_postal_code)
            or utils.is_empty_str(address_country)
            or utils.is_empty_str(address_city)
        ):

            missing_required_data_err = "Please provide your full address"
            self.toggle_form_err(missing_required_data_err)

        if not missing_required_data_err:
            # save user
            result: IntentResult = self.on_form_submit(
                title=subtitle,
                name=name,
                email=email,
                phone=phone_number,
                street=address_street,
                street_num=address_number,
                postal_code=address_postal_code,
                city=address_city,
                country=address_country,
                website=website,
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
        self.name_field = views.TTextField(
            label="Name",
            hint="your name",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_NAME,
        )
        self.email_field = views.TTextField(
            label="Email",
            hint="your email address",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_EMAIL,
        )
        self.phone_field = views.TTextField(
            label="Phone (optional)",
            hint="your phone number",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_PHONE,
        )
        self.subtitle_field = views.TTextField(
            label="Job Title",
            hint="What is your role as a freelancer?",
            on_focus=self.on_field_focus,
            keyboard_type=utils.KEYBOARD_TEXT,
        )
        self.website_field = views.TTextField(
            label="Website (optional)",
            hint="URL of your website.",
        )
        self.street_field = views.TTextField(
            label="Street Name",
            expand=1,
        )
        self.street_number_field = views.TTextField(
            label="Street Number",
            keyboard_type=utils.KEYBOARD_NUMBER,
            expand=1,
        )
        self.postal_code_field = views.TTextField(
            label="Postal Code",
            keyboard_type=utils.KEYBOARD_NUMBER,
            expand=1,
        )

        self.city_field = views.TTextField(
            label="City",
            expand=1,
        )
        self.country_field = views.TTextField(
            label="Country",
        )
        self.form_err_control = views.TErrorText("")
        self.submit_btn = views.TPrimaryButton(
            on_click=self.on_submit_btn_clicked,
            label=self.submit_btn_label,
        )
        return Column(
            spacing=dimens.SPACE_MD,
            controls=[
                self.subtitle_field,
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
        self.name_field.value = user.name
        self.email_field.value = user.email
        self.phone_field.value = user.phone_number
        self.subtitle_field.value = user.subtitle
        self.street_field.value = user.address.street
        self.postal_code_field.value = user.address.postal_code
        self.street_number_field.value = user.address.number
        self.city_field.value = user.address.city
        self.country_field.value = user.address.country
        self.website_field.value = user.website
        self.update()


class SplashScreen(TView, UserControl):
    """Displayed the first time the app loads

    Checks if user has been created
    If created, redirects user to the homepage
    If not created, displays a create user form
    """

    def __init__(
        self,
        params: TViewParams,
        on_install_demo_data: Callable,
    ):
        super().__init__(params=params)
        self.keep_back_stack = False  # User cannot go back from this screen
        self.intent = AuthIntent()
        self.client_storage = params.client_storage
        self.on_install_demo_data = on_install_demo_data

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
        """when the user clicks on the proceed with demo data button"""
        self.on_install_demo_data()  # install demo data
        self.navigate_to_route(res_utils.HOME_SCREEN_ROUTE)  # navigate to home screen

    def did_mount(self):
        self.mounted = True
        self.show_login_if_signed_out_else_redirect()

    def build(self):
        self.loading_indicator = views.TProgressBar()
        self.form_container = Column(
            controls=[
                # views.TAppLogoWithLabel(),
                views.THeadingWithSubheading(
                    "Welcome to Tuttle",
                    "Let's get you started: Please enter your details below. Your data will be stored locally and will not be sent to a server.",
                ),
                self.loading_indicator,
                views.Spacer(),
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
                            views.Spacer(md_space=True),
                            views.TImage(
                                image_paths.splashImgPath,
                                "welcome screen image",
                                width=300,
                            ),
                            views.THeadingWithSubheading(
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
                            views.TSecondaryButton(
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


class ProfileMenuItemsHandler:
    """Manages profile's main-menu items"""

    def __init__(
        self,
        params: TViewParams,
    ):
        super().__init__()
        self.menu_title = "My Profile"
        self.items = [
            views.NavigationMenuItem(
                index=0,
                label="Profile Photo",
                icon=utils.TuttleComponentIcons.profile_photo_icon,
                selected_icon=utils.TuttleComponentIcons.profile_photo_selected_icon,
                destination=ProfilePhotoContent(params=params),
            ),
            views.NavigationMenuItem(
                index=1,
                label="Personal Info",
                icon=utils.TuttleComponentIcons.profile_icon,
                selected_icon=utils.TuttleComponentIcons.profile_selected_icon,
                destination=UserInfoContent(params=params),
            ),
            views.NavigationMenuItem(
                index=1,
                label="Payment Settings",
                icon=utils.TuttleComponentIcons.payment_icon,
                selected_icon=utils.TuttleComponentIcons.payment_selected_icon,
                destination=PaymentInfoContent(params=params),
            ),
        ]


def profile_destination_content_wrapper(
    controls: list[
        UserControl,
    ],
):
    """returns a container that wraps the destination content"""
    # ADD SPACING TO THE TOP OF THE CONTENT
    controls.insert(0, views.Spacer(md_space=True))
    return Column(
        spacing=dimens.SPACE_STD,
        run_spacing=0,
        controls=controls,
    )


class ProfilePhotoContent(TView, UserControl):
    """Content for profile photo"""

    def __init__(self, params: TViewParams):
        super().__init__(params)
        self.intent = AuthIntent()
        self.uploaded_photo_path = ""
        self.user_profile: User = None

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
            upload_url = self.upload_file_callback(file)
            if upload_url:
                self.uploaded_photo_path = upload_url

    def uploading_profile_pic_progress_listener(self, e):
        """Callback for when profile photo is being uploaded"""
        if e.progress == 1.0:
            if self.uploaded_photo_path:
                result = self.intent.update_user_photo_path(
                    self.user_profile,
                    self.uploaded_photo_path,
                )
                # assume error occurred
                msg = result.error_msg
                is_err = True
                if result.was_intent_successful:
                    self.profile_photo_img.src = self.uploaded_photo_path
                    msg = "Profile photo updated"
                    is_err = False
                self.show_snack(msg, is_err)
                if is_err:
                    self.user_profile.profile_photo_path = ""
                self.uploaded_photo_path = None  # clear
            self.update_self()

    def build(self):
        self.profile_photo_img = views.TProfilePhotoImg()
        self.update_photo_btn = views.TSecondaryButton(
            label="Update Photo",
            on_click=self.on_update_photo_clicked,
        )
        self.profile_photo_content = [
            views.THeading(
                "Profile Photo",
                size=fonts.HEADLINE_4_SIZE,
            ),
            self.profile_photo_img,
            self.update_photo_btn,
        ]
        return profile_destination_content_wrapper(
            controls=self.profile_photo_content,
        )

    def did_mount(self):

        """Called when the view is mounted on page"""
        self.mounted = True
        result: IntentResult = self.intent.get_user_if_exists()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.user_profile: User = result.data
            if self.user_profile.profile_photo_path:
                self.profile_photo_img.src = self.user_profile.profile_photo_path
            self.update_self()

    def will_unmount(self):
        """Called when the view is unmounted from page"""
        self.mounted = False


class UserInfoContent(TView, UserControl):
    """Content for user info"""

    def __init__(self, params: TViewParams):
        super().__init__(params)
        self.intent = AuthIntent()
        self.user_profile: User = None

    def on_profile_updated(self, data):
        """Callback for when user profile has been updated successfully"""
        self.show_snack("Your profile has been updated")
        self.user_profile: User = data

    def build(self):
        """Builds the view"""
        self.user_info_form = UserDataForm(
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
            submit_btn_label="Save",
        )
        self.user_info_content = [
            views.THeading(
                "Personal Info",
                size=fonts.HEADLINE_4_SIZE,
            ),
            self.user_info_form,
        ]
        return profile_destination_content_wrapper(self.user_info_content)

    def did_mount(self):

        """Called when the view is mounted on page"""
        self.mounted = True
        result: IntentResult = self.intent.get_user_if_exists()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.user_profile: User = result.data
            # refresh user data form
            self.user_info_form.refresh_user_info(self.user_profile)
            self.update_self()

    def will_unmount(self):
        """Called when the view is unmounted from page"""
        self.mounted = False


class PaymentInfoContent(TView, UserControl):
    """Content for payment info"""

    def __init__(self, params: TViewParams):
        super().__init__(params)
        self.intent = AuthIntent()
        self.user_profile: User = None

    def on_update_payment_info(self, user: User):
        """Callback for when user updates their payment information"""
        result: IntentResult = self.intent.update_user(user)
        if result.was_intent_successful:
            self.show_snack("Payment information updated successfully")
            self.user_profile = result.data
            self.payment_data_form.update_form_data(user=self.user_profile)
        else:
            self.show_snack(result.error_msg, is_error=True)

    def build(self):
        self.payment_data_form = PaymentDataForm(
            on_form_submit=self.on_update_payment_info,
        )
        self.payment_info_content = [
            views.THeading(
                "Payment Settings",
                size=fonts.HEADLINE_4_SIZE,
            ),
            self.payment_data_form,
        ]
        return profile_destination_content_wrapper(self.payment_info_content)

    def did_mount(self):
        """Called when the view is mounted on page"""
        self.mounted = True
        result: IntentResult = self.intent.get_user_if_exists()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
            self.navigate_back()  # navigate out
        else:
            self.user_profile: User = result.data
            # setup payment info form
            self.payment_data_form.update_form_data(user=self.user_profile)
            self.update_self()

    def will_unmount(self):
        """Called when the view is unmounted from page"""
        self.mounted = False


class ProfileScreen(TView, UserControl):
    """User profile screen"""

    def __init__(self, params: TViewParams):
        super().__init__(params=params)
        self.preferences_intent = PreferencesIntent(
            client_storage=params.client_storage,
        )
        self.menu_handler = ProfileMenuItemsHandler(
            params=params,
        )
        self.current_menu_index = 0
        # initialize the side bar menu
        self.side_bar_menu = views.TNavigationMenu(
            title=self.menu_handler.menu_title,
            destinations=self.get_menu_destinations(),
            on_change=lambda e: self.on_menu_destination_change(e),
            top_margin=0,
        )
        # initialize the destination view to the first menu item's destination
        self.destination_view = self.menu_handler.items[
            self.current_menu_index
        ].destination

    def get_menu_destinations(self):
        """Returns the destinations for the navigation menu"""
        items = []
        for item in self.menu_handler.items:
            itemDestination = NavigationRailDestination(
                icon_content=Icon(
                    item.icon,
                    size=dimens.ICON_SIZE,
                ),
                selected_icon_content=Icon(
                    item.selected_icon,
                    size=dimens.ICON_SIZE,
                ),
                label_content=views.TBodyText(item.label),
                padding=padding.symmetric(horizontal=dimens.SPACE_SM),
            )
            items.append(itemDestination)
        return items

    def on_menu_destination_change(self, e):
        """Handles menu destination change"""
        if self.mounted:
            self.current_menu_index: int = e.control.selected_index
            menu_item = self.menu_handler.items[self.current_menu_index]
            self.destination_view = menu_item.destination
            self.destination_content_container.content = self.destination_view
            self.update_self()

    def build(self):
        """Builds the profile screen"""
        self.destination_content_container = Container(
            padding=padding.all(dimens.SPACE_MD),
            content=self.destination_view,
            col={
                "xs": 7,
                "md": 8,
                "lg": 9,
            },
        )
        self.side_bar = Container(
            col={"xs": 4, "md": 3, "lg": 2},
            padding=padding.only(top=dimens.SPACE_SM),
            content=Column(
                controls=[
                    Container(
                        IconButton(
                            icon=icons.KEYBOARD_ARROW_LEFT,
                            on_click=self.navigate_back,
                            icon_size=dimens.MD_ICON_SIZE,
                        ),
                        padding=padding.symmetric(vertical=dimens.SPACE_STD),
                    ),
                    self.side_bar_menu,
                ]
            ),
            alignment=alignment.center,
            border=border.only(
                right=border.BorderSide(
                    width=0.2,
                    color=colors.BORDER_DARK_COLOR,
                )
            ),
        )

        self.profile_screen_view = ResponsiveRow(
            controls=[
                self.side_bar,
                self.destination_content_container,
            ],
            spacing=0,
            alignment=utils.START_ALIGNMENT,
            vertical_alignment=utils.START_ALIGNMENT,
            expand=1,
        )
        return self.profile_screen_view

    def did_mount(self):
        """Called when the view is mounted on page"""
        self.mounted = True
        self.load_preferred_theme()

    def load_preferred_theme(self):
        """Sets the UI theme from the user's preferences"""
        result = self.preferences_intent.get_preferred_theme()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)
            return
        self.preferred_theme = result.data
        side_bar_components = [
            self.side_bar,
            self.side_bar_menu,
        ]
        side_bar_bg_color = colors.SIDEBAR_DARK_COLOR  # default is dark mode
        if self.preferred_theme == theme.THEME_MODES.light.value:
            side_bar_bg_color = colors.SIDEBAR_LIGHT_COLOR
        for component in side_bar_components:
            component.bgcolor = side_bar_bg_color
        self.update_self()

    def on_window_resized_listener(self, width, height):
        if not self.mounted:
            return
        super().on_window_resized_listener(width, height)
        self.profile_screen_view.height = self.page_height
        self.destination_content_container.height = self.page_height
        self.update_self()

    def will_unmount(self):
        """Called when the view is unmounted from page"""
        self.mounted = False
