import flet
from flet import (
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    Page,
    Row,
    Text,
    icons,
    Radio,
    RadioGroup,
    Column,
)


def main(page: Page):
    def on_time_tracking_preference_change(event):
        pass

    # a RadioGroup group of radio buttons to select from the following options: Calendar File, Cloud Calendar, Spreadsheet
    time_tracking_preference = RadioGroup(
        Column(
            [
                Radio(label="Calendar File", value="calendar_file"),
                Radio(label="Cloud Calendar", value="cloud_calendar"),
                Radio(label="Spreadsheet", value="spreadsheet"),
            ],
        ),
        on_change=on_time_tracking_preference_change,
    )

    def on_file_picked(result: FilePickerResultEvent):
        picked_file = result.files[0]
        selected_file_display.value = picked_file.path
        selected_file_display.update()

    pick_file_dialog = FilePicker(on_result=on_file_picked)
    selected_file_display = Text()

    page.overlay.append(pick_file_dialog)

    page.add(
        Column(
            [
                time_tracking_preference,
                Row(
                    [
                        ElevatedButton(
                            "Select file",
                            icon=icons.UPLOAD_FILE,
                            on_click=lambda _: pick_file_dialog.pick_files(
                                allow_multiple=False
                            ),
                        ),
                        selected_file_display,
                    ]
                ),
                ElevatedButton(
                    "Import data",
                    icon=icons.IMPORT_EXPORT,
                ),
            ]
        )
    )


flet.app(target=main)
