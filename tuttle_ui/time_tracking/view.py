from flet import (
    Column,
    Container,
    GridView,
    ResponsiveRow,
    Text,
    UserControl,
    Radio,
    RadioGroup,
    FilePicker,
    FilePickerResultEvent,
    Row,
    ElevatedButton,
    icons,
)

import core
import res

from .intent import TimeTrackingIntentImpl


class TimeTrackingView(core.abstractions.TuttleView, UserControl):
    """Screen for time tracking data entry"""

    def __init__(self, navigate_to_route, show_snack, dialog_controller, local_storage):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = TimeTrackingIntentImpl(local_storage=local_storage)
        self.loading_indicator = core.views.horizontal_progress

        self.time_tracking_preference = RadioGroup(
            Row(
                [
                    Radio(label="Calendar File", value="calendar_file"),
                    Radio(label="Cloud Calendar", value="cloud_calendar"),
                    Radio(label="Spreadsheet", value="spreadsheet"),
                ],
            ),
            on_change=lambda e: None,
        )

        self.pick_file_dialog = FilePicker(on_result=self.on_file_picked)
        # TODO: add to page
        #     page.overlay.append(pick_file_dialog)

        self.selected_file_display = Text()

        # page.overlay.append(pick_file_dialog)

        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        core.views.get_headline_txt(
                            txt="My Time Tracking", size=res.fonts.HEADLINE_4_SIZE
                        ),
                        self.loading_indicator,
                        self.time_tracking_preference,
                        Row(
                            [
                                ElevatedButton(
                                    "Select file",
                                    icon=icons.UPLOAD_FILE,
                                    on_click=lambda _: self.pick_file_dialog.pick_files(
                                        allow_multiple=False
                                    ),
                                ),
                                self.selected_file_display,
                            ]
                        ),
                        ElevatedButton(
                            "Import data",
                            icon=icons.IMPORT_EXPORT,
                        ),
                    ],
                )
            ]
        )

    def on_file_picked(self, result: FilePickerResultEvent):
        picked_file = result.files[0]
        self.selected_file_display.value = picked_file.path
        self.selected_file_display.update()

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.loading_indicator.visible = False

            if self.mounted:
                self.update()
        except Exception as e:
            # logger
            print(f"exception raised @time_tracking.did_mount {e}")

    def build(self):
        return Column(
            controls=[
                self.title_control,
            ]
        )

    def will_unmount(self):
        self.mounted = False
