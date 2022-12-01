import typing
from typing import Callable, Optional
from core.date_time_utils import get_last_seven_days
from flet import (
    Card,
    Column,
    Container,
    Icon,
    IconButton,
    Row,
    Text,
    TextButton,
    UserControl,
    icons,
    padding,
)

from core.abstractions import TuttleView
from core.constants_and_enums import (
    CENTER_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_JUSTIFY,
    AlertDialogControls,
)
from core.models import IntentResult
from core.views import (
    horizontal_progress,
    mdSpace,
    AlertDisplayPopUp,
    ConfirmDisplayPopUp,
)
from projects.intent_impl import ProjectsIntentImpl
from projects.project_model import Project
from res import colors, dimens, fonts
from res.dimens import MIN_WINDOW_WIDTH
from res.strings import (
    CLIENT_ID_LBL,
    CONTRACT_ID_LBL,
    DELETE_PROJECT,
    EDIT_PROJECT,
    END_DATE,
    HASH_TAG,
    MARK_AS_COMPLETE,
    PROJECT_DESC_LBL,
    PROJECT_LBL,
    PROJECT_STATUS_LBL,
    START_DATE,
    VIEW_CLIENT_HINT,
    VIEW_CLIENT_LBL,
    VIEW_CONTRACT_HINT,
    VIEW_CONTRACT_LBL,
)
from res.utils import PROJECT_EDITOR_SCREEN_ROUTE
from core.charts import BarChart


class ViewProjectScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        on_navigate_back,
        local_storage,
        project_id: str,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            on_navigate_back=on_navigate_back,
        )
        self.intent_handler = ProjectsIntentImpl(local_storage=local_storage)
        self.project_id = project_id
        self.loading_indicator = horizontal_progress
        self.project: Optional[Project] = None
        self.dialog = None
        self.chart = None

    def display_project_data(self):
        self.project_title_control.value = self.project.title
        self.client_control.value = self.project.contract.client.title
        self.contract_control.value = self.project.contract.title
        self.project_description_control.value = self.project.description
        self.project_start_date_control.value = (
            f"{START_DATE}: {self.project.start_date}"
        )
        self.project_end_date_control.value = f"{END_DATE}: {self.project.end_date}"
        self.project_status_control.value = (
            f"{PROJECT_STATUS_LBL} {self.project.get_status()}"
        )
        self.project_tagline_control.value = f"{HASH_TAG}{self.project.unique_tag}"
        self.set_chart()

    def set_chart(self):
        dummy_hours = []
        last_seven = get_last_seven_days()
        for i in range(0, len(last_seven)):
            dummy_hours.append((i + 1) * 10)

        self.chart = BarChart(
            x_items_labels=last_seven,
            values=dummy_hours,
            chart_title="Hours logged last 7 days",
            x_label="Days",
            y_lbl="Hours",
            legend="hours per day",
        )
        self.chart_container.content = self.chart

    def did_mount(self):
        try:
            self.mounted = True
            result: IntentResult = self.intent_handler.get_project_by_id(
                self.project_id
            )
            if not result.was_intent_successful:
                self.show_snack(result.error_msg, True)
            else:
                self.project = result.data
                self.display_project_data()
            self.loading_indicator.visible = False
            if self.mounted:
                self.update()
        except Exception as e:
            # log
            print(f"Exception raised @view_project_screen.did_mount {e}")

    def on_view_client_clicked(self, e):
        self.show_snack("Coming soon", False)

    def on_view_contract_clicked(self, e):
        self.show_snack("Coming soon", False)

    def on_mark_as_complete_clicked(self, e):
        if self.dialog:
            self.dialog.close_dialog()
        self.dialog = AlertDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Un Implemented Error",
            description="This feature is coming soon!",
        )
        self.dialog.open_dialog()

    def on_edit_clicked(self, e):
        if self.project is None:
            # project is not loaded yet
            return
        self.navigate_to_route(PROJECT_EDITOR_SCREEN_ROUTE, self.project.id)

    def on_delete_clicked(self, e):
        if self.dialog:
            self.dialog.close_dialog()
        self.dialog = ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description="Are you sure you wish to delete this project?",
            on_proceed=self.on_delete_confirmed,
            proceed_button_lbl="Yes! Delete",
        )
        self.dialog.open_dialog()

    def on_delete_confirmed(
        self,
    ):
        self.show_snack("Un Implemented feature!", True)

    def window_on_resized(self, desired_width, height):
        super().window_on_resized(desired_width, height)
        desired_width = self.page_width * 0.4
        min_chart_width = MIN_WINDOW_WIDTH * 0.7
        chart_width = (
            desired_width if desired_width > min_chart_width else min_chart_width
        )
        self.chart_container.width = chart_width
        self.update()

    def build(self):
        """Called when page is built"""
        self.edit_project_btn = IconButton(
            icon=icons.EDIT_OUTLINED,
            tooltip=EDIT_PROJECT,
            on_click=self.on_edit_clicked,
        )
        self.mark_as_complete_btn = IconButton(
            icon=icons.CHECK_CIRCLE_OUTLINE,
            icon_color=colors.PRIMARY_COLOR,
            tooltip=MARK_AS_COMPLETE,
            on_click=self.on_mark_as_complete_clicked,
        )
        self.delete_project_btn = IconButton(
            icon=icons.DELETE_OUTLINE_ROUNDED,
            icon_color=colors.ERROR_COLOR,
            tooltip=DELETE_PROJECT,
            on_click=self.on_delete_clicked,
        )

        self.project_title_control = Text(size=fonts.SUBTITLE_1_SIZE)
        self.client_control = Text(
            size=fonts.SUBTITLE_2_SIZE,
            color=colors.GRAY_COLOR,
        )
        self.contract_control = Text(
            size=fonts.SUBTITLE_2_SIZE,
            color=colors.GRAY_COLOR,
        )
        self.project_description_control = Text(
            size=fonts.BODY_1_SIZE,
            text_align=TXT_ALIGN_JUSTIFY,
        )

        self.project_start_date_control = Text(
            size=fonts.BUTTON_SIZE,
            color=colors.GRAY_COLOR,
            font_family=fonts.HEADLINE_FONT,
        )
        self.project_end_date_control = Text(
            size=fonts.BUTTON_SIZE,
            color=colors.GRAY_COLOR,
            font_family=fonts.HEADLINE_FONT,
        )

        self.project_status_control = Text(
            size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR
        )
        self.project_tagline_control = Text(
            size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR
        )

        self.chart_container = Container()

        page_view = Row(
            [
                Container(
                    padding=padding.all(dimens.SPACE_STD),
                    width=int(MIN_WINDOW_WIDTH * 0.3),
                    content=Column(
                        controls=[
                            IconButton(
                                icon=icons.KEYBOARD_ARROW_LEFT,
                                on_click=self.on_navigate_back,
                            ),
                            TextButton(
                                VIEW_CLIENT_LBL,
                                tooltip=VIEW_CLIENT_HINT,
                                on_click=self.on_view_client_clicked,
                            ),
                            TextButton(
                                VIEW_CONTRACT_LBL,
                                tooltip=VIEW_CONTRACT_HINT,
                                on_click=self.on_view_contract_clicked,
                            ),
                        ]
                    ),
                ),
                Container(
                    expand=True,
                    padding=padding.all(dimens.SPACE_MD),
                    content=Column(
                        controls=[
                            self.loading_indicator,
                            Row(
                                controls=[
                                    Icon(icons.WORK_ROUNDED),
                                    Column(
                                        expand=True,
                                        spacing=0,
                                        run_spacing=0,
                                        controls=[
                                            Row(
                                                vertical_alignment=CENTER_ALIGNMENT,
                                                alignment=SPACE_BETWEEN_ALIGNMENT,
                                                controls=[
                                                    Text(
                                                        PROJECT_LBL,
                                                        size=fonts.HEADLINE_4_SIZE,
                                                        font_family=fonts.HEADLINE_FONT,
                                                        color=colors.PRIMARY_COLOR,
                                                    ),
                                                    Row(
                                                        vertical_alignment=CENTER_ALIGNMENT,
                                                        alignment=SPACE_BETWEEN_ALIGNMENT,
                                                        spacing=dimens.SPACE_STD,
                                                        run_spacing=dimens.SPACE_STD,
                                                        controls=[
                                                            self.edit_project_btn,
                                                            self.mark_as_complete_btn,
                                                            self.delete_project_btn,
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            self.project_title_control,
                                            self.client_control,
                                            self.contract_control,
                                        ],
                                    ),
                                ],
                            ),
                            mdSpace,
                            Text(
                                PROJECT_DESC_LBL,
                                size=fonts.SUBTITLE_1_SIZE,
                            ),
                            self.project_description_control,
                            self.project_start_date_control,
                            self.project_end_date_control,
                            mdSpace,
                            self.chart_container,
                            mdSpace,
                            Row(
                                spacing=dimens.SPACE_STD,
                                run_spacing=dimens.SPACE_STD,
                                alignment=START_ALIGNMENT,
                                vertical_alignment=CENTER_ALIGNMENT,
                                controls=[
                                    Card(
                                        Container(
                                            self.project_status_control,
                                            padding=padding.all(dimens.SPACE_SM),
                                        ),
                                        elevation=2,
                                    ),
                                    Card(
                                        Container(
                                            self.project_tagline_control,
                                            padding=padding.all(dimens.SPACE_SM),
                                        ),
                                        elevation=2,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
            spacing=dimens.SPACE_XS,
            run_spacing=dimens.SPACE_MD,
            alignment=START_ALIGNMENT,
            vertical_alignment=START_ALIGNMENT,
            expand=True,
        )
        return page_view

    def will_unmount(self):
        self.mounted = False
        if self.dialog:
            self.dialog.dimiss_open_dialogs()
