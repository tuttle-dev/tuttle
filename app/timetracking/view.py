from typing import Callable, Optional

from pathlib import Path
from loguru import logger

from flet import (
    AlertDialog,
    Column,
    Container,
    FilePickerResultEvent,
    FilePickerUploadEvent,
    ResponsiveRow,
    Text,
    UserControl,
    border,
)

from core import tabular, utils, views
from core.abstractions import DialogHandler, TuttleView, IntentResult
from pandas import DataFrame
from res import colors, dimens, fonts, res_utils

from tuttle.calendar import Calendar
from tuttle.cloud import CloudConnector

from .intent import TimeTrackingIntent


class TwoFAPopUp(DialogHandler):
    """Prompts user for the two_factor_verification_code during cloud configuration"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_submit_callback: Callable[[str], None],
        title: Optional[str] = "Enter the verification code",
    ):

        dialog_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)
        title = title
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.get_heading(title=title, size=fonts.HEADLINE_4_SIZE),
                        views.xsSpace,
                        views.get_std_txt_field(
                            label="Code",
                            on_change=self.on_code_changed,
                        ),
                        views.xsSpace,
                    ],
                ),
                width=dialog_width,
            ),
            actions=[
                views.get_primary_btn(
                    label="Verify",
                    on_click=lambda e: on_submit_callback(self.code),
                ),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)

        self.code = ""

    def on_code_changed(self, e):
        self.code = e.control.value


class NewTimeTrackPopUp(DialogHandler):
    """Prompts user to request a timetrack sheet or calendar file or cloud calendar"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_use_file_callback: Callable[[bool, bool], None],
        on_use_cloud_acc_callback: Callable[[str, str, str, str], None],
        preferred_cloud_acc: str,
        preferred_acc_provider: str,
    ):
        display_cloud_option = (
            True if preferred_cloud_acc and preferred_acc_provider else False
        )

        space_between_cloud_controls = views.xsSpace
        space_between_cloud_controls.visible = display_cloud_option
        dialog_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)
        title = "Track your progress"
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.get_heading(title=title, size=fonts.HEADLINE_4_SIZE),
                        views.xsSpace,
                        views.get_body_txt(
                            f"Use calendar from {preferred_acc_provider}",
                            show=display_cloud_option,
                        ),
                        space_between_cloud_controls,
                        views.get_std_txt_field(
                            label="Calendar Name",
                            on_change=self.on_calendar_name_changed,
                            show=display_cloud_option,
                        ),
                        space_between_cloud_controls,
                        views.get_std_txt_field(
                            label="Cloud Password",
                            hint="Your password will not be stored",
                            keyboard_type=utils.KEYBOARD_PASSWORD,
                            on_change=self.on_password_changed,
                            show=display_cloud_option,
                        ),
                        space_between_cloud_controls,
                        views.get_primary_btn(
                            label="Load from cloud calendar",
                            icon="cloud",
                            on_click=lambda e: on_use_cloud_acc_callback(
                                account_id=preferred_cloud_acc,
                                provider=preferred_acc_provider,
                                password=self.password,
                                calendar_name=self.calendar_name,
                            ),
                            width=int(dialog_width * 0.9),
                            show=display_cloud_option,
                        ),
                        space_between_cloud_controls,
                        views.get_or_txt(show_lines=False, show=display_cloud_option),
                        space_between_cloud_controls,
                        views.get_secondary_btn(
                            label="Upload a calendar (.ics) file",
                            icon="calendar_month",
                            on_click=lambda _: on_use_file_callback(is_ics=True),
                            width=int(dialog_width * 0.9),
                        ),
                        views.get_or_txt(show_lines=False),
                        views.xsSpace,
                        views.get_secondary_btn(
                            label="Upload a spreadsheet",
                            icon="table_view",
                            on_click=lambda _: on_use_file_callback(
                                is_spreadsheet=True
                            ),
                            width=int(dialog_width * 0.9),
                        ),
                        views.xsSpace,
                    ],
                ),
                width=dialog_width,
            ),
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.password = ""
        self.calendar_name = ""

    def on_calendar_name_changed(self, e):
        self.calendar_name = e.control.value

    def on_password_changed(self, e):
        self.password = e.control.value


class TimeTrackingView(TuttleView, UserControl):
    """Time tracking view on home page"""

    def __init__(self, params):
        super().__init__(params)
        self.intent = TimeTrackingIntent(client_storage=params.client_storage)
        self.preferred_cloud_acc = ""
        self.preferred_cloud_provider = ""
        self.pop_up_handler = None
        self.dataframe_to_display: Optional[DataFrame] = None

    def close_pop_up_if_open(self):
        if self.pop_up_handler:
            self.pop_up_handler.close_dialog()

    def parent_intent_listener(self, intent: str, data: any):
        if intent == res_utils.RELOAD_INTENT:
            self.initialize_data()
            return

        if intent == res_utils.NEW_TIME_TRACK_INTENT:
            self.close_pop_up_if_open()
            self.pop_up_handler = NewTimeTrackPopUp(
                dialog_controller=self.dialog_controller,
                on_use_file_callback=self.on_add_timetrack_from_file,
                on_use_cloud_acc_callback=self.on_login_to_cloud,
                preferred_cloud_acc=self.preferred_cloud_acc,
                preferred_acc_provider=self.preferred_cloud_provider,
            )
            self.pop_up_handler.open_dialog()
        return

    """GETTING DATA FROM A FILE"""

    def on_add_timetrack_from_file(
        self,
        is_spreadsheet: Optional[bool] = False,
        is_ics: Optional[bool] = False,
    ):
        """Open file picker to select a file to upload"""
        self.close_pop_up_if_open()
        allowed_exts = ["ics"] if is_ics else ["xlsx", "csv", "xls", "tsv", "ods"]
        title = "Select .ics file" if is_ics else "Select excel file"
        self.pick_file_callback(
            on_file_picker_result=self.on_file_picker_result,
            on_upload_progress=self.on_upload_progress,
            allowed_extensions=allowed_exts,
            dialog_title=title,
            file_type="custom",
        )
        self.set_progress_hint()

    def on_file_picker_result(self, e: FilePickerResultEvent):
        """Handle file picker result"""
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.set_progress_hint(f"Uploading file {file.name}")
            self.upload_file_callback(file)
            upload_path = Path(file.path)
            if upload_path:
                self.uploaded_file_path = upload_path
        else:
            self.set_progress_hint(hide_progress=True)

    def on_upload_progress(self, e: FilePickerUploadEvent):
        """Handle file upload progress"""
        if e.progress == 1.0:
            # upload complete
            self.set_progress_hint(f"Upload complete, processing file...")
            intent_result = self.intent.process_timetracking_file(
                self.uploaded_file_path,
            )
            msg = (
                "New work progress recorded."
                if intent_result.was_intent_successful
                else intent_result.error_msg
            )
            is_error = not intent_result.was_intent_successful
            self.show_snack(msg, is_error)
            if intent_result.was_intent_successful:
                self.dataframe_to_display = intent_result.data
                self.update_timetracking_dataframe()
                self.display_dataframe()
            self.set_progress_hint(hide_progress=True)

    """Cloud calendar setup"""

    def on_login_to_cloud(
        self,
        account_id: str,
        calendar_name: str,
        password: str,
        provider: str,
    ):
        """
        This function is used for logging in to a cloud account.

        Parameters:
        ----------
            - account_id (str): The ID of the cloud account to log in to.
            - calendar_name (str): The name of the calendar to load data from.
            - password (str): The password for the account.
            - provider (str): The name of the cloud provider (e.g. Google, iCloud).
        """
        self.close_pop_up_if_open()
        if utils.is_empty_str(account_id):
            self.show_snack("No Cloud account was specified")
            return
        if utils.is_empty_str(calendar_name):
            self.show_snack("No calendar name was provided")
            return

        if utils.is_empty_str(password):
            self.show_snack("Your Cloud password is required")
            return

        progress_msg = "Authenticating your account..."
        self.set_progress_hint(progress_msg)
        result: IntentResult[CloudConnector] = self.intent.connect_to_cloud(
            account_id=account_id,
            provider=provider,
            password=password,
        )

        self.set_progress_hint(hide_progress=True)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)
            return  # exit function

        # get connector object
        connector: CloudConnector = result.data

        if connector.requires_2fa:
            # request 2FA code
            self.request_2fa_code(connector=connector, calendar_name=calendar_name)
            return  #   exit function
        self.show_snack(f"Cloud login successful.")

        # load calendar data
        self.load_calendar_from_cloud(
            calendar_name=calendar_name,
            connector=connector,
        )

    def request_2fa_code(
        self,
        connector: CloudConnector,
        calendar_name: str,
    ):
        """
        This function is used to request a 2FA code from the user.

        Parameters:
        ----------
            - connector (CloudConnector): The connector object for the cloud account.
            - calendar_name (str): The name of the calendar to load data from.
        """
        logger.info(f"Requesting 2FA code for {connector.account_name}")
        self.close_pop_up_if_open()
        self.pop_up_handler = TwoFAPopUp(
            self.dialog_controller,
            on_submit_callback=lambda code: self.verify_cloud_connector(
                two_fa_code=code, connector=connector, calendar_name=calendar_name
            ),
        )
        self.pop_up_handler.open_dialog()

    def verify_cloud_connector(
        self,
        connector: CloudConnector,
        two_fa_code: str,
        calendar_name: str,
    ):
        """
        This function is used to verify a 2FA code provided by the user.
        It takes in the following parameters:
        - connector (CloudConnector): The connector object for the cloud account.
        - two_fa_code (str): The 2FA code provided by the user.
        - calendar_name (str): The name of the calendar to load data from.
        """
        connector.validate_2fa_code(twofa_code=two_fa_code)
        if not connector.is_connected:
            self.request_2fa_code(
                connector=connector,
                calendar_name=calendar_name,
            )
            self.show_snack(
                "The code you provided is incorrect",
                is_error=True,
            )
            return
        self.load_calendar_from_cloud(
            calendar_name=calendar_name,
            connector=connector,
        )

    def load_calendar_from_cloud(
        self,
        calendar_name: str,
        connector: CloudConnector,
    ):
        self.set_progress_hint(msg="Loading calendar data")
        result: IntentResult[DataFrame] = self.intent.load_from_cloud_calendar(
            cloud_connector=connector,
            calendar_name=calendar_name,
        )
        self.set_progress_hint(hide_progress=True)
        if not result.was_intent_successful:
            self.show_snack(
                result.error_msg,
                is_error=True,
            )
            return
        self.dataframe_to_display = result.data
        self.update_timetracking_dataframe()
        self.display_dataframe()

    """ DISPLAYED DATA FRAME """

    def load_existing_dataframe(self):
        result = self.intent.get_timetracking_data()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)
            return
        if isinstance(result.data, DataFrame):
            self.dataframe_to_display = result.data

    def update_timetracking_dataframe(self):
        result = self.intent.set_timetracking_data(self.dataframe_to_display)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)

    def display_dataframe(self):
        if not isinstance(self.dataframe_to_display, DataFrame):
            return
        data_table = tabular.data_frame_to_data_table(
            data_frame=self.dataframe_to_display.sort_index().reset_index(),
            table_style={
                "border": border.all(),
                "border_radius": 10,
            },
        )
        self.timetracked_container.content = data_table

    def show_no_recorded_timetracks(self):
        self.no_timetrack_control.visible = True

    def load_preferred_cloud_acc(self):
        result = self.intent.get_preferred_cloud_account()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)
            return
        self.preferred_cloud_provider = result.data[0]
        self.preferred_cloud_acc = result.data[1]

    def set_progress_hint(self, msg: str = "", hide_progress=False):
        if self.mounted:
            self.loading_indicator.visible = not hide_progress
            self.ongoing_action_hint.value = msg
            self.ongoing_action_hint.visible = not hide_progress
            self.update_self()

    def did_mount(self):
        self.mounted = True
        self.initialize_data()

    def initialize_data(self):
        self.loading_indicator.visible = True
        self.load_preferred_cloud_acc()
        self.load_existing_dataframe()
        self.display_dataframe()
        self.loading_indicator.visible = False
        self.update_self()

    def build(self):
        self.loading_indicator = views.horizontal_progress
        self.no_timetrack_control = views.get_body_txt(
            txt="You have not logged any work progress yet.",
            color=colors.ERROR_COLOR,
            show=False,
        )
        self.ongoing_action_hint = views.get_body_txt(show=False)
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.get_heading(
                            title="Time Tracking", size=fonts.HEADLINE_4_SIZE
                        ),
                        self.loading_indicator,
                        self.ongoing_action_hint,
                        self.no_timetrack_control,
                    ],
                )
            ]
        )
        self.timetracked_container = Container(expand=True)
        return Column(
            controls=[
                self.title_control,
                views.mdSpace,
                self.timetracked_container,
            ]
        )

    def will_unmount(self):
        self.mounted = False
        if self.pop_up_handler:
            self.pop_up_handler.dimiss_open_dialogs()
