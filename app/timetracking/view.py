from typing import Callable, Optional

from pathlib import Path

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
from core.abstractions import DialogHandler, TuttleView
from pandas import DataFrame
from res import colors, dimens, fonts, res_utils

from tuttle.calendar import Calendar

from .intent import TimeTrackingIntent
from .model import CloudCalendarInfo, CloudConfigurationResult


class TwoFAPopUp(DialogHandler):
    """Prompts user for the two_factor_verification_code during cloud configuration"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_submit: Callable,
        title: Optional[str] = "Enter the verification code",
    ):

        dialog_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)
        title = title
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.get_headline_txt(txt=title, size=fonts.HEADLINE_4_SIZE),
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
                    on_click=self.on_submit_btn_clicked,
                ),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.on_submit_callback = on_submit
        self.code = ""

    def on_code_changed(self, e):
        self.code = e.control.value

    def on_submit_btn_clicked(self, e):
        self.close_dialog()
        self.on_submit_callback(self.code)


class NewTimeTrackPopUp(DialogHandler):
    """Prompts user to request a timetrack sheet or calendar file or cloud calendar"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_submit: Callable,
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
                        views.get_headline_txt(txt=title, size=fonts.HEADLINE_4_SIZE),
                        views.xsSpace,
                        views.get_body_txt(
                            f"Use calendar from {preferred_cloud_acc}",
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
                            on_click=lambda e: self.on_submit_btn_clicked(
                                is_cloud=True
                            ),
                            width=int(dialog_width * 0.9),
                            show=display_cloud_option,
                        ),
                        space_between_cloud_controls,
                        views.get_or_txt(show_lines=False, show=display_cloud_option),
                        space_between_cloud_controls,
                        views.get_secondary_btn(
                            label="Upload a spreadsheet",
                            icon="table_view",
                            on_click=lambda _: self.on_submit_btn_clicked(
                                is_spreadsheet=True
                            ),
                            width=int(dialog_width * 0.9),
                        ),
                        views.xsSpace,
                        views.get_or_txt(show_lines=False),
                        views.xsSpace,
                        views.get_secondary_btn(
                            label="Upload a calendar (.ics) file",
                            icon="calendar_month",
                            on_click=lambda _: self.on_submit_btn_clicked(is_ics=True),
                            width=int(dialog_width * 0.9),
                        ),
                    ],
                ),
                width=dialog_width,
            ),
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.on_submit_callback = on_submit
        self.acc = preferred_cloud_acc
        self.provider = preferred_acc_provider
        self.password = ""
        self.calendar_name = ""

    def on_calendar_name_changed(self, e):
        self.calendar_name = e.control.value

    def on_password_changed(self, e):
        self.password = e.control.value

    def on_submit_btn_clicked(self, is_spreadsheet=False, is_ics=False, is_cloud=False):
        info = (
            None
            if not is_cloud
            else CloudCalendarInfo(
                account=self.acc,
                calendar_name=self.calendar_name,
                password=self.password,
                provider=self.provider,
            )
        )

        self.close_dialog()
        self.on_submit_callback(
            is_spreadsheet=is_spreadsheet,
            is_ics=is_ics,
            is_cloud=is_cloud,
            cloud_calendar_info=info,
        )


class TimeTrackingView(TuttleView, UserControl):
    """Time tracking view on home page"""

    def __init__(self, params):
        super().__init__(params)
        self.intent = TimeTrackingIntent(local_storage=params.local_storage)
        self.preferred_cloud_acc = ""
        self.preferred_cloud_provider = ""
        self.pop_up_handler = None
        self.dataframe_to_display: DataFrame = None

    def close_pop_up_if_open(self):
        if self.pop_up_handler:
            self.pop_up_handler.close_dialog()

    def parent_intent_listener(self, intent: str, data: any):
        if self.loading_indicator.visible:
            return  # action in progress

        if intent == res_utils.NEW_TIME_TRACK_INTENT:
            self.close_pop_up_if_open()
            self.pop_up_handler = NewTimeTrackPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=self.on_add_new_timetrack_record_callback,
                preferred_cloud_acc=self.preferred_cloud_acc,
                preferred_acc_provider=self.preferred_cloud_provider,
            )
            self.pop_up_handler.open_dialog()
        return

    # TODO: refactor this - an enum TimeTrackingMethod or so would have been better
    def on_add_new_timetrack_record_callback(
        self,
        is_spreadsheet=False,
        is_ics=False,
        is_cloud=False,
        cloud_calendar_info: Optional[CloudCalendarInfo] = None,
    ):
        """Spreadsheet and ics uploads"""
        self.close_pop_up_if_open()
        if is_spreadsheet or is_ics:
            exts = ["ics"] if is_ics else ["xlsx", "csv", "xls", "tsv", "ods"]
            title = "Select .ics file" if is_ics else "Select excel file"
            self.pick_file_callback(
                on_file_picker_result=self.on_file_picker_result,
                on_upload_progress=self.on_upload_progress,
                allowed_extensions=exts,
                dialog_title=title,
                file_type="custom",
            )
            self.set_progress_hint()

        elif is_cloud:
            self.on_load_from_calendar(info=cloud_calendar_info)

    def on_file_picker_result(self, e: FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.set_progress_hint(f"Uploading file {file.name}")
            self.upload_file_callback(file)
            upload_url = Path(file.path)
            if upload_url:
                self.uploaded_file_url = upload_url
        else:
            self.set_progress_hint(hide_progress=True)

    def on_upload_progress(self, e: FilePickerUploadEvent):

        if e.progress == 1.0:
            self.set_progress_hint(f"Upload complete, processing file...")
            intent_result = self.intent.process_timetracking_file(
                self.uploaded_file_url, e.file_name
            )
            msg = (
                "New work progress recorded."
                if intent_result.was_intent_successful
                else intent_result.error_msg
            )
            is_error = not intent_result.was_intent_successful
            self.show_snack(msg, is_error)
            if intent_result.was_intent_successful:
                data: Calendar = intent_result.data
                self.dataframe_to_display = data.to_data()
                self.update_timetracking_dataframe()
                self.display_dataframe()
            self.set_progress_hint(hide_progress=True)

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

    """Cloud calendar setup"""

    def request_2fa_auth_code(
        self,
        info: CloudCalendarInfo,
        prev_un_verified_login_res: CloudConfigurationResult,
    ):
        self.close_pop_up_if_open()
        self.pop_up_handler = TwoFAPopUp(
            self.dialog_controller,
            on_submit=lambda code: self.on_load_from_calendar(
                info=info,
                two_factor_auth_code=code,
                prev_un_verified_login_res=prev_un_verified_login_res,
            ),
        )
        self.pop_up_handler.open_dialog()

    def on_load_from_calendar(
        self,
        info: CloudCalendarInfo,
        two_factor_auth_code: Optional[str] = "",
        prev_un_verified_login_res: Optional[CloudConfigurationResult] = None,
    ):

        if utils.is_empty_str(info.account):
            self.show_snack("No Cloud account was specified")
            return

        if utils.is_empty_str(info.calendar_name):
            self.show_snack("No calendar name was provided")
            return

        if utils.is_empty_str(info.password):
            self.show_snack("Your Cloud password is required")
            return

        progress_msg = (
            "Authenticating your account..."
            if not two_factor_auth_code
            else "Verifying your account..."
        )
        self.set_progress_hint(progress_msg)

        result = self.intent.configure_account_and_load_calendar(
            info,
            two_factor_code=two_factor_auth_code,
            prev_un_verified_login_res=prev_un_verified_login_res,
        )
        if not result.was_intent_successful:
            # the intent failed
            self.show_snack(result.error_msg, is_error=True)
            self.set_progress_hint(hide_progress=True)
            return
        # if we get here, then intent was a success
        # Case 1 - a 2fa is needed
        result_data: CloudConfigurationResult = result.data
        if result_data.request_2fa_code:
            if result_data.provided_2fa_code_is_invalid:
                self.show_snack(
                    "The code you provided is invalid. Please retry", is_error=True
                )
            """prompt user for the 2fa code, then call this method again"""
            self.request_2fa_auth_code(
                info=info,
                prev_un_verified_login_res=result_data,
            )
        else:
            feedback_msg = ""
            is_error = False
            if result_data.calendar_loaded_successfully:
                feedback_msg = "Processed your calendar info"
            elif result_data.auth_error_occurred:
                feedback_msg = "Invalid credentials. Your account name or password might be incorrect."
                is_error = True
            else:
                feedback_msg = "Failed to load calendar info"
                is_error = True
            is_error = not result_data.calendar_loaded_successfully
            self.show_snack(feedback_msg, is_error)
        self.set_progress_hint(hide_progress=True)

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
        if result.was_intent_successful:
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
        self.loading_indicator.visible = True
        self.load_preferred_cloud_acc()
        self.load_existing_dataframe()
        self.display_dataframe()
        self.loading_indicator.visible = False
        self.update_self()

    def build(self):
        self.loading_indicator = views.horizontal_progress
        self.no_timetrack_control = Text(
            value="You have not logged any work progress yet.",
            color=colors.ERROR_COLOR,
            visible=False,
        )
        self.ongoing_action_hint = Text("", visible=False)
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.get_headline_txt(
                            txt="Time Tracking", size=fonts.HEADLINE_4_SIZE
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
