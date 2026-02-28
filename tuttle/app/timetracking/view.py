from typing import Callable, Optional

from pathlib import Path
from loguru import logger

from flet import (
    AlertDialog,
    Column,
    Container,
    ResponsiveRow,
    Text,
    Control,
    Border,
)

from ..core import tabular, utils, views
from ..core.abstractions import DialogHandler, TView
from ..core.intent_result import IntentResult
from pandas import DataFrame
from ..res import colors, dimens, fonts, res_utils

from .data_source import SYSTEM_CALENDAR_AVAILABLE
from .intent import TimeTrackingIntent


class NewTimeTrackPopUp(DialogHandler):
    """Prompts user to load time tracking data from a system calendar, .ics file, or spreadsheet."""

    def __init__(
        self,
        dialog_controller: Callable[[any, utils.AlertDialogControls], None],
        on_use_file_callback: Callable[[bool, bool], None],
        on_use_system_calendar_callback: Callable[[str], None],
        system_calendars: list[dict],
        system_calendar_error: str = "",
    ):
        dialog_width = 480
        title = "Track your progress"

        has_calendars = len(system_calendars) > 0
        needs_permission = (
            SYSTEM_CALENDAR_AVAILABLE
            and not has_calendars
            and bool(system_calendar_error)
        )
        show_calendar_picker = SYSTEM_CALENDAR_AVAILABLE and has_calendars
        calendar_names = [c["title"] for c in system_calendars] if has_calendars else []

        self._calendar_dropdown = views.TDropDown(
            label="Calendar",
            items=calendar_names,
            hint="Select a calendar synced to this device",
            show=show_calendar_picker,
        )

        permission_hint = views.TBodyText(
            txt=(
                "Calendar access required. Please grant calendar "
                "permission to this app in your system settings, "
                "then restart."
            ),
            color=colors.text_muted,
            show=needs_permission,
        )

        dialog = AlertDialog(
            bgcolor=colors.bg_surface,
            content=Container(
                content=Column(
                    scroll=utils.AUTO_SCROLL,
                    controls=[
                        views.THeading(title=title, size=fonts.HEADLINE_4_SIZE),
                        views.Spacer(xs_space=True),
                        views.TBodyText(
                            "Load from Calendar",
                            show=SYSTEM_CALENDAR_AVAILABLE,
                        ),
                        views.Spacer(xs_space=True),
                        permission_hint,
                        self._calendar_dropdown,
                        views.Spacer(xs_space=True),
                        views.TPrimaryButton(
                            label="Load from calendar",
                            icon="calendar_month",
                            on_click=lambda _: on_use_system_calendar_callback(
                                self._calendar_dropdown.value,
                            ),
                            show=show_calendar_picker,
                        ),
                        views.Spacer(xs_space=True),
                        views.OrView(show_lines=False, show=SYSTEM_CALENDAR_AVAILABLE),
                        views.Spacer(xs_space=True),
                        views.TSecondaryButton(
                            label="Upload a calendar (.ics) file",
                            icon="calendar_month",
                            on_click=lambda _: on_use_file_callback(is_ics=True),
                        ),
                        views.OrView(show_lines=False),
                        views.Spacer(xs_space=True),
                        views.TSecondaryButton(
                            label="Upload a spreadsheet",
                            icon="table_view",
                            on_click=lambda _: on_use_file_callback(
                                is_spreadsheet=True,
                            ),
                        ),
                        views.Spacer(xs_space=True),
                    ],
                ),
                width=dialog_width,
            ),
        )
        super().__init__(dialog=dialog, dialog_controller=dialog_controller)


class TimeTrackingView(TView, Column):
    """Time tracking view on home page"""

    def __init__(self, params):
        super().__init__(params)
        self.intent = TimeTrackingIntent(client_storage=params.client_storage)
        self.pop_up_handler = None
        self._system_calendars: list[dict] = []
        self._system_calendar_error: str = ""
        object.__setattr__(self, "dataframe_to_display", None)

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
                on_use_system_calendar_callback=self.on_load_from_system_calendar,
                system_calendars=self._system_calendars,
                system_calendar_error=self._system_calendar_error,
            )
            self.pop_up_handler.open_dialog()
        return

    # --- System Calendar ---

    def on_load_from_system_calendar(self, calendar_name: Optional[str]):
        self.close_pop_up_if_open()
        if not calendar_name:
            self.show_snack("Please select a calendar", is_error=True)
            return
        self.set_progress_hint(f"Loading calendar '{calendar_name}'...")
        result: IntentResult[DataFrame] = self.intent.load_from_system_calendar(
            calendar_name=calendar_name,
        )
        self.set_progress_hint(hide_progress=True)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)
            return
        object.__setattr__(self, "dataframe_to_display", result.data)
        self.update_timetracking_dataframe()
        self.display_dataframe()
        self.show_snack("Calendar data loaded.")

    # --- File upload ---

    def on_add_timetrack_from_file(
        self,
        is_spreadsheet: Optional[bool] = False,
        is_ics: Optional[bool] = False,
    ):
        """Open file picker to select a file to upload"""
        self.close_pop_up_if_open()
        if not is_spreadsheet and not is_ics:
            return
        allowed_exts = ["ics"] if is_ics else ["xlsx", "csv", "xls", "tsv", "ods"]
        title = "Select .ics file" if is_ics else "Select excel file"
        self.pick_file_callback(
            on_file_picker_result=self.on_file_picker_result,
            allowed_extensions=allowed_exts,
            dialog_title=title,
            file_type="custom",
        )
        self.set_progress_hint()

    def on_file_picker_result(self, e):
        """Handle file picker result"""
        if e.files and len(e.files) > 0:
            file = e.files[0]
            self.set_progress_hint(f"Uploading file {file.name}")
            upload_path = Path(file.path)
            if upload_path:
                self.uploaded_file_path = upload_path
                self.extract_dataframe_from_file()
        else:
            self.set_progress_hint(hide_progress=True)

    def extract_dataframe_from_file(self):
        """Execute intent to process file"""
        if not self.uploaded_file_path:
            return
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
            object.__setattr__(self, "dataframe_to_display", intent_result.data)
            self.update_timetracking_dataframe()
            self.display_dataframe()
        self.set_progress_hint(hide_progress=True)

    # --- DataFrame display ---

    def load_existing_dataframe(self):
        result = self.intent.get_timetracking_data()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)
            return
        if isinstance(result.data, DataFrame):
            object.__setattr__(self, "dataframe_to_display", result.data)

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
                "border": Border.all(),
                "border_radius": 10,
            },
        )
        self.timetracked_container.content = data_table

    def show_no_recorded_timetracks(self):
        self.no_timetrack_control.visible = True

    def _load_system_calendars(self):
        """Fetch available system calendars (best-effort)."""
        result = self.intent.list_system_calendars()
        if result.was_intent_successful and result.data:
            self._system_calendars = result.data
            self._system_calendar_error = ""
        else:
            self._system_calendar_error = result.error_msg or ""

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
        self._load_system_calendars()
        self.load_existing_dataframe()
        self.display_dataframe()
        self.loading_indicator.visible = False
        self.update_self()

    def build(self):
        self.loading_indicator = views.TProgressBar()
        self.no_timetrack_control = views.TBodyText(
            txt="You have not logged any work progress yet.",
            color=colors.text_muted,
            show=False,
        )
        self.ongoing_action_hint = views.TBodyText(show=False)
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.THeading(
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
        self.controls = [
            self.title_control,
            views.Spacer(md_space=True),
            self.timetracked_container,
        ]

    def will_unmount(self):
        self.mounted = False
        if self.pop_up_handler:
            self.pop_up_handler.dimiss_open_dialogs()
