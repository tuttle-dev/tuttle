from typing import Callable
import flet as ft
from flet import (
    AlertDialog,
    Column,
    Container,
    ResponsiveRow,
    FilePickerUploadEvent,
    Text,
    UserControl,
)
from .model import ICloudCalendarInfo
from .intent import TimeTrackingIntent
from core.abstractions import DialogHandler, TuttleView
from core.utils import AUTO_SCROLL, AlertDialogControls, KEYBOARD_PASSWORD, is_empty_str
from core.models import IntentResult
from core.views import (
    get_headline_txt,
    get_std_txt_field,
    get_secondary_btn,
    get_primary_btn,
    horizontal_progress,
    mdSpace,
    xsSpace,
)
from res.colors import ERROR_COLOR
from res.dimens import MIN_WINDOW_WIDTH
from res.fonts import HEADLINE_4_SIZE
from res.utils import NEW_TIME_TRACK_INTENT


class TimeTrackFromIcloudPopUp(DialogHandler):
    """Loads time track data from an icloud calendar"""

    def __init__(
        self,
        dialog_controller: Callable[[any, AlertDialogControls], None],
        on_submit: Callable,
        preferred_icloud_acc: str,
    ):

        dialog_width = int(MIN_WINDOW_WIDTH * 0.8)
        title = "Load work progress from iCloud Calendar"
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    scroll=AUTO_SCROLL,
                    controls=[
                        get_headline_txt(txt=title, size=HEADLINE_4_SIZE),
                        xsSpace,
                        get_std_txt_field(
                            lbl="iCloud Acc",
                            initial_value=preferred_icloud_acc,
                            on_change=self.on_icloud_acc_changed,
                        ),
                        xsSpace,
                        get_std_txt_field(
                            lbl="Calendar Name", on_change=self.on_calendar_name_changed
                        ),
                        xsSpace,
                        get_std_txt_field(
                            lbl="iCloud Password",
                            keyboard_type=KEYBOARD_PASSWORD,
                            on_change=self.on_password_changed,
                        ),
                        xsSpace,
                    ],
                ),
                width=dialog_width,
            ),
            actions=[
                get_primary_btn(label="Load data", on_click=self.on_submit_btn_clicked),
            ],
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.acc = preferred_icloud_acc
        self.password = ""
        self.calendar_name = ""
        self.on_submit = on_submit

    def on_icloud_acc_changed(self, e):
        self.acc = e.control.value

    def on_calendar_name_changed(self, e):
        self.calendar_name = e.control.value

    def on_password_changed(self, e):
        self.password = e.control.value

    def on_submit_btn_clicked(self, e):
        info = ICloudCalendarInfo(
            account=self.acc, calendar_name=self.calendar_name, password=self.password
        )
        self.close_dialog()
        self.on_submit(info)


class NewTimeTrackPopUp(DialogHandler):
    """Prompts user to request a timetrack sheet or calendar file or cloud calendar"""

    def __init__(
        self,
        dialog_controller: Callable[[any, AlertDialogControls], None],
        on_submit: Callable,
        preferred_icloud_acc: str,
    ):

        dialog_width = int(MIN_WINDOW_WIDTH * 0.8)
        title = "Track your progress"
        icloud_acc_btn_title = (
            f"Use {preferred_icloud_acc}"
            if preferred_icloud_acc
            else "Setup iCloud calendar"
        )
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    scroll=AUTO_SCROLL,
                    controls=[
                        get_headline_txt(txt=title, size=HEADLINE_4_SIZE),
                        xsSpace,
                        get_secondary_btn(
                            label="Upload as excel file",
                            on_click=lambda _: self.on_submit_btn_clicked(
                                is_spreadsheet=True
                            ),
                            width=240,
                        ),
                        xsSpace,
                        get_secondary_btn(
                            label="Upload a .ics file",
                            on_click=lambda _: self.on_submit_btn_clicked(is_ics=True),
                            width=240,
                        ),
                        xsSpace,
                        get_secondary_btn(
                            label=icloud_acc_btn_title,
                            on_click=lambda _: self.on_submit_btn_clicked(
                                is_icloud=True
                            ),
                            width=(dialog_width * 0.7),
                        ),
                        xsSpace,
                    ],
                ),
                width=dialog_width,
            )
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)
        self.on_submit_callback = on_submit

    def on_submit_btn_clicked(
        self, is_spreadsheet=False, is_ics=False, is_icloud=False
    ):
        self.close_dialog()
        self.on_submit_callback(
            is_spreadsheet=is_spreadsheet, is_ics=is_ics, is_icloud=is_icloud
        )


class TimetracksView(TuttleView, UserControl):
    """Time tracking view on home page"""

    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        local_storage,
        upload_file_callback: Callable,
        pick_file_callback: Callable,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = TimeTrackingIntent(local_storage=local_storage)

        self.upload_file_callback = upload_file_callback
        self.pick_file_callback = pick_file_callback
        self.loading_indicator = horizontal_progress
        self.no_timetrack_control = Text(
            value="You have not logged any work progress yet.",
            color=ERROR_COLOR,
            visible=False,
        )
        self.ongoing_action_hint = Text("", visible=False)
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt="Time Tracking", size=HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.ongoing_action_hint,
                        self.no_timetrack_control,
                    ],
                )
            ]
        )
        self.timetracked_container = Container()
        self.timetracks_recorded = {}
        self.preferred_icloud_acc = ""
        self.new_pop_up_handler = None
        self.icloud_calendar_config_handler = None

    def parent_intent_listener(self, intent: str, data: any):
        if self.loading_indicator.visible:
            return  # action in progress

        if intent == NEW_TIME_TRACK_INTENT:
            self.new_pop_up_handler = NewTimeTrackPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=self.on_add_new_timetrack_record,
                preferred_icloud_acc=self.preferred_icloud_acc,
            )
            self.new_pop_up_handler.open_dialog()
        return

    def on_add_new_timetrack_record(
        self, is_spreadsheet=False, is_ics=False, is_icloud=False
    ):
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

        elif is_icloud:
            self.icloud_calendar_config_handler = TimeTrackFromIcloudPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=self.on_load_from_calendar,
                preferred_icloud_acc=self.preferred_icloud_acc,
            )
            self.icloud_calendar_config_handler.open_dialog()

    """Spreadsheet and ics uploads"""

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.set_progress_hint(f"Uploading file {file.name}")
            self.upload_file_callback(file)

    def on_upload_progress(self, e: FilePickerUploadEvent):
        if e.progress == 1.0:
            self.set_progress_hint(f"Upload complete, processing file...")
            result = self.intent_handler.process_timetracking_file(e.file_name)
            msg = (
                "New work progress recorded."
                if result.was_intent_successful
                else result.error_msg
            )
            is_error = not result.was_intent_successful
            self.show_snack(msg, is_error)
            self.set_progress_hint(hide_progress=True)

    """Icloud calendar setup"""

    def on_load_from_calendar(self, info: ICloudCalendarInfo):
        if self.loading_indicator.visible:
            return  # on going action

        if is_empty_str(info.account):
            self.show_snack("No iCloud account was specified")
            return

        if is_empty_str(info.calendar_name):
            self.show_snack("No calendar name was provided")
            return

        if is_empty_str(info.password):
            self.show_snack("Your iCloud password is required")
            return

        self.set_progress_hint(f"Loading data from your calendar...")

        save_icloud_acc_as_preferred = is_empty_str(self.preferred_icloud_acc)
        result = self.intent_handler.configure_icloud_and_load_calendar(
            info, save_icloud_acc_as_preferred
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

    def load_preferred_icloud_acc(self):
        icloud_acc_res = self.intent_handler.get_preferred_icloud_account()
        if icloud_acc_res.was_intent_successful:
            self.preferred_icloud_acc = icloud_acc_res.data

    def set_progress_hint(self, msg: str = "", hide_progress=False):
        if self.mounted:
            self.loading_indicator.visible = not hide_progress
            self.ongoing_action_hint.value = msg
            self.ongoing_action_hint.visible = not hide_progress
            self.update()

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.load_recorded_timetracks()
            count = len(self.timetracks_recorded)
            self.loading_indicator.visible = False
            if count == 0:
                self.show_no_recorded_timetracks()
            else:
                self.refresh_records()

            self.load_preferred_icloud_acc()
            if self.mounted:
                self.update()
        except Exception as e:
            print(f"exception raised @timetracking.TimetracksView.did_mount {e}")

    def build(self):

        view = Column(
            controls=[
                self.title_control,
                mdSpace,
                Container(self.timetracked_container, expand=True),
            ]
        )
        return view

    def will_unmount(self):
        try:
            self.mounted = False
            if self.new_pop_up_handler:
                self.new_pop_up_handler.dimiss_open_dialogs()
            if self.icloud_calendar_config_handler:
                self.icloud_calendar_config_handler.dimiss_open_dialogs()
        except Exception as e:
            print(e)
