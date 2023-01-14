from typing import Callable, Optional

from flet import (
    AlertDialog,
    FilePickerResultEvent,
    Column,
    Container,
    ResponsiveRow,
    FilePickerUploadEvent,
    Text,
    UserControl,
    ProgressRing,
)
from preferences.model import CloudAccounts
from .model import CloudCalendarInfo
from .intent import TimeTrackingIntent
from core.abstractions import DialogHandler, TuttleView
from core import views, utils
from res import colors, fonts, res_utils, dimens


class NewTimeTrackPopUp(DialogHandler):
    """Prompts user to request a timetrack sheet or calendar file or cloud calendar"""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_submit: Callable,
        preferred_cloud_acc: str,
        preferred_acc_provider: str,
    ):

        dialog_width = int(dimens.MIN_WINDOW_WIDTH * 0.8)
        title = "Track your progress"
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.get_headline_txt(txt=title, size=fonts.HEADLINE_4_SIZE),
                        views.xsSpace,
                        views.get_dropdown(
                            label="Cloud Provider",
                            items=[item.value for item in CloudAccounts],
                            initial_value=preferred_acc_provider,
                            on_change=self.on_cloud_provider_changed,
                        ),
                        views.xsSpace,
                        views.get_std_txt_field(
                            label="Cloud Acc",
                            initial_value=preferred_cloud_acc,
                            on_change=self.on_cloud_acc_changed,
                        ),
                        views.xsSpace,
                        views.get_std_txt_field(
                            label="Calendar Name",
                            on_change=self.on_calendar_name_changed,
                        ),
                        views.xsSpace,
                        views.get_std_txt_field(
                            label="Cloud Password",
                            keyboard_type=utils.KEYBOARD_PASSWORD,
                            on_change=self.on_password_changed,
                        ),
                        views.xsSpace,
                        views.get_primary_btn(
                            label="Load from cloud calendar",
                            on_click=lambda e: self.on_submit_btn_clicked(
                                is_cloud=True
                            ),
                            width=int(dialog_width * 0.9),
                        ),
                        views.xsSpace,
                        views.get_or_txt(),
                        views.xsSpace,
                        views.get_secondary_btn(
                            label="Upload a spreadsheet",
                            icon="table_view",
                            on_click=lambda _: self.on_submit_btn_clicked(
                                is_spreadsheet=True
                            ),
                            width=int(dialog_width * 0.9),
                        ),
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

    def on_cloud_provider_changed(self, e):
        self.provider = e.control.value

    def on_cloud_acc_changed(self, e):
        self.acc = e.control.value

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
        self.timetracks_recorded = {}
        self.preferred_cloud_acc = ""
        self.preferred_cloud_provider = ""
        self.pop_up_handler = None

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

    def on_add_new_timetrack_record_callback(
        self,
        is_spreadsheet=False,
        is_ics=False,
        is_cloud=False,
        cloud_calendar_info: Optional[CloudCalendarInfo] = None,
    ):

        self.close_pop_up_if_open()
        if is_spreadsheet or is_ics:
            exts = ["ics"] if is_ics else ["xlsx"]
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

    """Spreadsheet and ics uploads"""

    def on_file_picker_result(self, e: FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.set_progress_hint(f"Uploading file {file.name}")
            upload_url = self.upload_file_callback(file)
            if upload_url:
                self.uploaded_file_url = upload_url
        else:
            self.set_progress_hint(hide_progress=True)

    def on_upload_progress(self, e: FilePickerUploadEvent):

        if e.progress == 1.0:
            self.set_progress_hint(f"Upload complete, processing file...")
            result = self.intent.process_timetracking_file_intent(
                self.uploaded_file_url, e.file_name
            )
            msg = (
                "New work progress recorded."
                if result.was_intent_successful
                else result.error_msg
            )
            is_error = not result.was_intent_successful
            self.show_snack(msg, is_error)
            self.set_progress_hint(hide_progress=True)

    """Cloud calendar setup"""

    def on_load_from_calendar(self, info: CloudCalendarInfo):
        if utils.is_empty_str(info.account):
            self.show_snack("No Cloud account was specified")
            return

        if utils.is_empty_str(info.calendar_name):
            self.show_snack("No calendar name was provided")
            return

        if utils.is_empty_str(info.password):
            self.show_snack("Your Cloud password is required")
            return

        self.set_progress_hint(f"Authenticating your account...")

        save_cloud_acc_as_preferred = utils.is_empty_str(self.preferred_cloud_acc)
        result = self.intent.configure_account_and_load_calendar_intent(
            info,
            save_cloud_acc_as_preferred,
        )
        msg = (
            "Processed your calendar info"
            if result.was_intent_successful
            else "Failed to load calendar info"
        )
        is_error = not result.was_intent_successful
        self.show_snack(msg, is_error)
        self.set_progress_hint(hide_progress=True)

    def load_recorded_timetracks(self):
        self.timetracks_recorded = {}

    def refresh_records(self):
        self.timetracked_container.controls.clear()
        for key in self.timetracks_recorded:
            timetrack_data = self.timetracks_recorded[key]
            # TODO create card and add to list?

    def show_no_recorded_timetracks(self):
        self.no_timetrack_control.visible = True

    def load_preferred_cloud_acc(self):
        result = self.intent.get_preferred_cloud_account_intent()
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
        self.load_recorded_timetracks()
        count = len(self.timetracks_recorded)
        self.loading_indicator.visible = False
        if count == 0:
            self.show_no_recorded_timetracks()
        else:
            self.refresh_records()

        self.load_preferred_cloud_acc()
        self.update_self()

    def build(self):
        self.loading_indicator = ProgressRing(
            width=32,
            height=32,
        )
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
        self.timetracked_container = Column()
        return Column(
            controls=[
                self.title_control,
                views.mdSpace,
                Container(self.timetracked_container, expand=True),
            ]
        )

    def will_unmount(self):
        self.mounted = False
        if self.pop_up_handler:
            self.pop_up_handler.dimiss_open_dialogs()
