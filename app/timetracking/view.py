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


from core.abstractions import DialogHandler, TuttleView
from core.constants_and_enums import (
    AUTO_SCROLL,
    AlertDialogControls,
)
from core.models import IntentResult
from core.views import (
    get_headline_txt,
    get_secondary_btn,
    horizontal_progress,
    mdSpace,
    xsSpace,
)
from res.colors import ERROR_COLOR
from res.dimens import MIN_WINDOW_WIDTH
from res.fonts import HEADLINE_4_SIZE
from res.utils import NEW_TIME_TRACK_INTENT


class NewTimeTrackPopUp(DialogHandler):
    """Used to request a timetrack sheet or calendar file or cloud calendar"""

    def __init__(
        self,
        dialog_controller: Callable[[any, AlertDialogControls], None],
        on_submit: Callable,
    ):
        self.dialog_height = 550
        self.dialog_width = int(MIN_WINDOW_WIDTH * 0.8)
        self.half_of_dialog_width = int(MIN_WINDOW_WIDTH * 0.35)
        title = "Track your progress"
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    scroll=AUTO_SCROLL,
                    controls=[
                        get_headline_txt(txt=title, size=HEADLINE_4_SIZE),
                        xsSpace,
                        get_secondary_btn(
                            label="Upload as excel file",
                            on_click=lambda _: on_submit(is_spreadsheet=True),
                            width=240,
                        ),
                        xsSpace,
                        get_secondary_btn(
                            label="Upload a .ics file",
                            on_click=lambda _: on_submit(is_ics=True),
                            width=240,
                        ),
                        xsSpace,
                    ],
                ),
                width=self.dialog_width,
            )
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)


class TimetracksView(TuttleView, UserControl):
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
        self.intent_handler = None  # TODO
        self.upload_file_callback = upload_file_callback
        self.pick_file_callback = pick_file_callback
        self.loading_indicator = horizontal_progress
        self.no_timetrack_control = Text(
            value="You have not logged any work progress yet.",
            color=ERROR_COLOR,
            visible=False,
        )
        self.uploading_file_hint = Text("", visible=False)
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt="Time Tracking", size=HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.uploading_file_hint,
                        self.no_timetrack_control,
                    ],
                )
            ]
        )
        self.timetracked_container = Container()
        self.timetracks_recorded = {}
        self.editor = None

    def parent_intent_listener(self, intent: str, data: any):
        if self.loading_indicator.visible:
            return  # action in progress

        if intent == NEW_TIME_TRACK_INTENT:
            if self.editor:
                self.editor.close_dialog()
            self.editor = NewTimeTrackPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=self.on_new_timetrack_added,
            )
            self.editor.open_dialog()
        return

    def on_new_timetrack_added(self, is_spreadsheet=None, is_ics=None):
        self.loading_indicator.visible = True
        self.editor.close_dialog()
        try:
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
        except Exception as e:
            self.show_snack(f"an error occurred {e}", True)
            if self.mounted:
                self.loading_indicator.visible = False
                self.update()

        """result: IntentResult = None  # TODO
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            savedTimetrack = result.data
            # TODO refresh list
            self.show_snack("Recorded new work progress!", False)
        self.loading_indicator.visible = False """

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.uploading_file_hint.value = f"Uploading file {file.name}"
            self.uploading_file_hint.visible = True
            self.update()
            self.upload_file_callback(file)

    def on_upload_progress(self, e: FilePickerUploadEvent):
        if e.progress == 1.0:
            self.uploading_file_hint.value = f"Upload complete, processing file..."
            # TODO self.intent_handler.process_file(e.file_name)
            self.update()

    def load_recorded_timetracks(self):
        self.timetracks_recorded = {}

    def refresh_records(self):
        self.timetracked_container.controls.clear()
        for key in self.timetracks_recorded:
            timetrack_data = self.timetracks_recorded[key]
            # TODO create card and add to list?

    def show_no_recorded_timetracks(self):
        self.no_timetrack_control.visible = True

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
            if self.editor:
                self.editor.dimiss_open_dialogs()
        except Exception as e:
            print(e)
