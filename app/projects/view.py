from enum import Enum
from typing import Callable, Optional
from core.abstractions import TuttleViewParams
from flet import (
    ButtonStyle,
    Card,
    Column,
    Container,
    ElevatedButton,
    GridView,
    Icon,
    IconButton,
    ListTile,
    ResponsiveRow,
    Row,
    Text,
    TextButton,
    UserControl,
    border_radius,
    icons,
    margin,
    padding,
    FontWeight,
)

from core.abstractions import TuttleView
from core.charts import BarChart
from core import utils
from core.date_time_utils import get_last_seven_days
from core.intent_result import IntentResult
from core import views
from projects.intent import ProjectsIntent
from res import colors, dimens, fonts, res_utils

from tuttle.model import (
    Contract,
    Project,
)


class ProjectCard(UserControl):
    """Formats a single project info into a card ui display"""

    def __init__(
        self, project, on_view_details_clicked, on_delete_clicked, on_edit_clicked
    ):
        super().__init__()
        self.project: Project = project
        self.project_info_container = Column(run_spacing=0, spacing=0)
        self.on_view_details_clicked = on_view_details_clicked
        self.on_delete_clicked = on_delete_clicked
        self.on_edit_clicked = on_edit_clicked

    def build(self):
        self.project_info_container.controls = [
            ListTile(
                leading=Icon(utils.TuttleComponentIcons.project_icon),
                title=views.get_body_txt(self.project.title),
                subtitle=views.get_body_txt(
                    f"#{self.project.tag}",
                    color=colors.GRAY_COLOR,
                    weight=FontWeight.BOLD,
                ),
                trailing=views.view_edit_delete_pop_up(
                    on_click_view=lambda e: self.on_view_details_clicked(
                        self.project.id
                    ),
                    on_click_delete=lambda e: self.on_delete_clicked(self.project.id),
                    on_click_edit=lambda e: self.on_edit_clicked(self.project.id),
                ),
            ),
            views.mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "Brief Description",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Text(
                        self.project.get_brief_description(),
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                ],
                spacing=dimens.SPACE_XS,
                run_spacing=0,
                vertical_alignment=utils.CENTER_ALIGNMENT,
            ),
            views.mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "Client",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        Text(
                            self.project.client.name,
                            size=fonts.BODY_2_SIZE,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=utils.START_ALIGNMENT,
                vertical_alignment=utils.START_ALIGNMENT,
                spacing=dimens.SPACE_XS,
                run_spacing=0,
            ),
            views.mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "Contract",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        Text(
                            self.project.contract.title,
                            size=fonts.BODY_2_SIZE,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=utils.START_ALIGNMENT,
                vertical_alignment=utils.START_ALIGNMENT,
                spacing=dimens.SPACE_XS,
                run_spacing=0,
            ),
            views.mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "Start date",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        Text(
                            self.project.start_date.strftime("%d/%m/%Y")
                            if self.project.start_date
                            else "",
                            size=fonts.BODY_2_SIZE,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=utils.START_ALIGNMENT,
                vertical_alignment=utils.START_ALIGNMENT,
                spacing=dimens.SPACE_XS,
                run_spacing=0,
            ),
            views.mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "End date",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        Text(
                            self.project.end_date.strftime("%d/%m/%Y")
                            if self.project.end_date
                            else "-",
                            size=fonts.BODY_2_SIZE,
                            col={"xs": "12"},
                            color=colors.ERROR_COLOR,
                        ),
                    ),
                ],
                alignment=utils.START_ALIGNMENT,
                vertical_alignment=utils.START_ALIGNMENT,
                spacing=dimens.SPACE_XS,
                run_spacing=0,
            ),
            views.mdSpace,
        ]
        card = Card(
            elevation=2,
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(dimens.SPACE_STD),
                border_radius=border_radius.all(12),
                content=self.project_info_container,
            ),
        )
        return card


class ProjectStates(Enum):
    ALL = 1
    ACTIVE = 2
    COMPLETED = 3
    UPCOMING = 4


class ProjectFiltersView(UserControl):
    """Create and Handles projects view filtering buttons"""

    def __init__(self, onStateChanged: Callable[[ProjectStates], None]):
        super().__init__()
        self.currentState = ProjectStates.ALL
        self.stateTofilterButtonsMap = {}
        self.onStateChangedCallback = onStateChanged

    def filter_button(
        self, state: ProjectStates, label: str, onClick: Callable[[ProjectStates], None]
    ):
        button = ElevatedButton(
            text=label,
            col={"xs": 6, "sm": 3, "lg": 2},
            on_click=lambda e: onClick(state),
            height=dimens.CLICKABLE_PILL_HEIGHT,
            color=colors.PRIMARY_COLOR
            if state == self.currentState
            else colors.GRAY_COLOR,
            style=ButtonStyle(
                elevation={
                    utils.PRESSED: 3,
                    utils.SELECTED: 3,
                    utils.HOVERED: 4,
                    utils.OTHER_CONTROL_STATES: 2,
                },
            ),
        )
        return button

    def on_filter_button_clicked(self, state: ProjectStates):
        """sets the new state and updates selected button"""
        self.stateTofilterButtonsMap[self.currentState].color = colors.GRAY_COLOR
        self.currentState = state
        self.stateTofilterButtonsMap[self.currentState].color = colors.PRIMARY_COLOR
        self.update()
        self.onStateChangedCallback(state)

    def get_filter_button_label(self, state: ProjectStates):
        if state.value == ProjectStates.ACTIVE.value:
            return "Active"
        elif state.value == ProjectStates.UPCOMING.value:
            return "Upcoming"
        elif state.value == ProjectStates.COMPLETED.value:
            return "Completed"
        else:
            return "All"

    def set_filter_buttons(self):
        for state in ProjectStates:
            button = self.filter_button(
                label=self.get_filter_button_label(state),
                state=state,
                onClick=self.on_filter_button_clicked,
            )
            self.stateTofilterButtonsMap[state] = button

    def build(self):
        if len(self.stateTofilterButtonsMap) == 0:
            # set the buttons
            self.set_filter_buttons()

        self.filters = ResponsiveRow(
            controls=list(self.stateTofilterButtonsMap.values())
        )
        return self.filters


class ViewProjectScreen(TuttleView, UserControl):
    def __init__(
        self,
        params: TuttleViewParams,
        project_id: str,
    ):
        super().__init__(params)
        self.intent = ProjectsIntent()
        self.project_id = project_id
        self.loading_indicator = views.horizontal_progress
        self.project: Optional[Project] = None
        self.pop_up_handler = None
        self.chart = None

    def display_project_data(self):
        self.project_title_control.value = self.project.title
        self.client_control.value = self.project.contract.client.name
        self.contract_control.value = self.project.contract.title
        self.project_description_control.value = self.project.description
        self.project_start_date_control.value = f"Start Date: {self.project.start_date}"
        self.project_end_date_control.value = f"End Date: {self.project.end_date}"
        self.project_status_control.value = f"Status {self.project.get_status()}"
        self.project_tagline_control.value = f"#{self.project.tag}"
        # self.set_chart()

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
            y_label="Hours",
            legend="hours per day",
        )
        self.chart_container.content = self.chart

    def did_mount(self):
        self.mounted = True
        result: IntentResult = self.intent.get_project_by_id(self.project_id)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.project = result.data
            self.display_project_data()
        self.loading_indicator.visible = False
        self.update_self()

    def on_view_client_clicked(self, e):
        self.show_snack("Coming soon", False)

    def on_view_contract_clicked(self, e):
        self.show_snack("Coming soon", False)

    def on_mark_as_complete_clicked(self, e):
        if self.pop_up_handler:
            self.pop_up_handler.close_dialog()
        self.pop_up_handler = views.AlertDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Not Implemented",
            description="This feature is coming soon",
        )
        self.pop_up_handler.open_dialog()

    def on_edit_clicked(self, e):
        if self.project is None:
            # project is not loaded yet
            return
        self.navigate_to_route(res_utils.PROJECT_EDITOR_SCREEN_ROUTE, self.project.id)

    def on_delete_clicked(self, e):
        if self.project is None:
            # project is not loaded yet
            return
        if self.pop_up_handler:
            self.pop_up_handler.close_dialog()
        self.pop_up_handler = views.ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description=f"Are you sure you wish to delete this project\n{self.project.title}",
            on_proceed=self.on_delete_confirmed,
            proceed_button_label="Yes! Delete",
            data_on_confirmed=self.project.id,
        )
        self.pop_up_handler.open_dialog()

    def on_delete_confirmed(self, project_id):
        result = self.intent.delete_project_by_id(project_id)
        is_err = not result.was_intent_successful
        msg = result.error_msg if is_err else "Project deleted!"
        self.show_snack(msg, is_err)
        if not is_err:
            # go back
            self.on_navigate_back()

    def on_window_resized_listener(self, desired_width, height):
        super().on_window_resized_listener(desired_width, height)
        desired_width = self.page_width * 0.4
        min_chart_width = dimens.MIN_WINDOW_WIDTH * 0.7
        chart_width = (
            desired_width if desired_width > min_chart_width else min_chart_width
        )
        self.chart_container.width = chart_width
        self.update_self()

    def build(self):
        """Called when page is built"""
        self.edit_project_btn = IconButton(
            icon=icons.EDIT_OUTLINED,
            tooltip="Edit project",
            on_click=self.on_edit_clicked,
        )
        self.mark_as_complete_btn = IconButton(
            icon=icons.CHECK_CIRCLE_OUTLINE,
            icon_color=colors.PRIMARY_COLOR,
            tooltip="Mark as complete",
            on_click=self.on_mark_as_complete_clicked,
        )
        self.delete_project_btn = IconButton(
            icon=icons.DELETE_OUTLINE_ROUNDED,
            icon_color=colors.ERROR_COLOR,
            tooltip="Delete project",
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
            text_align=utils.TXT_ALIGN_JUSTIFY,
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
                    width=int(dimens.MIN_WINDOW_WIDTH * 0.3),
                    content=Column(
                        controls=[
                            IconButton(
                                icon=icons.KEYBOARD_ARROW_LEFT,
                                on_click=self.on_navigate_back,
                            ),
                            TextButton(
                                "Client",
                                tooltip="View project's client",
                                on_click=self.on_view_client_clicked,
                            ),
                            TextButton(
                                "Contract",
                                tooltip="View project's contract",
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
                                                vertical_alignment=utils.CENTER_ALIGNMENT,
                                                alignment=utils.SPACE_BETWEEN_ALIGNMENT,
                                                controls=[
                                                    Text(
                                                        "Project",
                                                        size=fonts.HEADLINE_4_SIZE,
                                                        font_family=fonts.HEADLINE_FONT,
                                                        color=colors.PRIMARY_COLOR,
                                                    ),
                                                    Row(
                                                        vertical_alignment=utils.CENTER_ALIGNMENT,
                                                        alignment=utils.SPACE_BETWEEN_ALIGNMENT,
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
                            views.mdSpace,
                            Text(
                                "Project Description",
                                size=fonts.SUBTITLE_1_SIZE,
                            ),
                            self.project_description_control,
                            self.project_start_date_control,
                            self.project_end_date_control,
                            views.mdSpace,
                            self.chart_container,
                            views.mdSpace,
                            Row(
                                spacing=dimens.SPACE_STD,
                                run_spacing=dimens.SPACE_STD,
                                alignment=utils.START_ALIGNMENT,
                                vertical_alignment=utils.CENTER_ALIGNMENT,
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
            alignment=utils.START_ALIGNMENT,
            vertical_alignment=utils.START_ALIGNMENT,
            expand=True,
        )
        return page_view

    def will_unmount(self):
        self.mounted = False
        if self.pop_up_handler:
            self.pop_up_handler.dimiss_open_dialogs()


class ProjectsListView(TuttleView, UserControl):
    def __init__(self, params):
        super().__init__(params)
        self.intent = ProjectsIntent()
        self.loading_indicator = views.horizontal_progress
        self.no_projects_control = Text(
            value="You have not added any projects yet.",
            color=colors.ERROR_COLOR,
            visible=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.get_headline_txt(
                            txt="My Projects", size=fonts.HEADLINE_4_SIZE
                        ),
                        self.loading_indicator,
                        self.no_projects_control,
                    ],
                )
            ]
        )
        self.projects_container = GridView(
            expand=False,
            max_extent=540,
            child_aspect_ratio=1.0,
            spacing=dimens.SPACE_STD,
            run_spacing=dimens.SPACE_MD,
        )
        self.projects_to_display = {}
        self.dialog = None

    def display_currently_filtered_projects(self):
        self.projects_container.controls.clear()
        for key in self.projects_to_display:
            project = self.projects_to_display[key]
            projectCard = ProjectCard(
                project=project,
                on_view_details_clicked=self.on_view_project_clicked,
                on_delete_clicked=self.on_delete_project_clicked,
                on_edit_clicked=self.on_edit_project_clicked,
            )
            self.projects_container.controls.append(projectCard)

    def on_view_project_clicked(self, project_id: str):
        self.navigate_to_route(res_utils.PROJECT_DETAILS_SCREEN_ROUTE, project_id)

    def on_delete_project_clicked(self, project_id: str):
        if project_id not in self.projects_to_display:
            return
        project_title = self.projects_to_display[project_id].title
        if self.dialog:
            self.dialog.close_dialog()
        self.dialog = views.ConfirmDisplayPopUp(
            dialog_controller=self.dialog_controller,
            title="Are You Sure?",
            description=f"Are you sure you wish to delete this project?\n{project_title}",
            on_proceed=self.on_delete_confirmed,
            data_on_confirmed=project_id,
            proceed_button_label="Yes! Delete",
        )
        self.dialog.open_dialog()

    def on_delete_confirmed(self, project_id):
        self.loading_indicator.visible = True
        self.update_self()
        result = self.intent.delete_project_by_id(project_id)
        is_err = not result.was_intent_successful
        if not is_err and project_id in self.projects_to_display:
            del self.projects_to_display[project_id]
            self.display_currently_filtered_projects()
        msg = result.error_msg if is_err else "Project deleted!"
        self.show_snack(msg, is_err)
        self.loading_indicator.visible = False
        self.update_self()

    def on_edit_project_clicked(self, project_id: str):
        self.navigate_to_route(res_utils.PROJECT_EDITOR_SCREEN_ROUTE, project_id)

    def on_filter_projects(self, filterByState: ProjectStates):
        if filterByState.value == ProjectStates.ACTIVE.value:
            self.projects_to_display = self.intent.get_active_projects_as_map()
        elif filterByState.value == ProjectStates.UPCOMING.value:
            self.projects_to_display = self.intent.get_upcoming_projects_as_map()
        elif filterByState.value == ProjectStates.COMPLETED.value:
            self.projects_to_display = self.intent.get_completed_projects_as_map()
        else:
            self.projects_to_display = self.intent.get_all_projects_as_map()
        self.display_currently_filtered_projects()
        self.update_self()

    def show_no_projects(self):
        self.no_projects_control.visible = True

    def did_mount(self):
        self.mounted = True
        self.loading_indicator.visible = True
        self.projects_to_display = self.intent.get_all_projects_as_map()
        count = len(self.projects_to_display)
        self.loading_indicator.visible = False
        if count == 0:
            self.show_no_projects()
        else:
            self.display_currently_filtered_projects()
        self.update_self()

    def build(self):
        return Column(
            controls=[
                self.title_control,
                views.mdSpace,
                ProjectFiltersView(onStateChanged=self.on_filter_projects),
                views.mdSpace,
                Container(self.projects_container, expand=True),
            ]
        )

    def will_unmount(self):
        self.mounted = False


class EditProjectScreen(TuttleView, UserControl):
    def __init__(
        self,
        params,
        project_id: str,
    ):
        super().__init__(
            params,
        )
        self.horizontal_alignment_in_parent = utils.CENTER_ALIGNMENT
        self.intent = ProjectsIntent()

        self.contracts_map = {}
        self.loading_indicator = views.horizontal_progress
        # info of project being edited
        self.project_id: int = int(project_id)
        self.project: Optional[Project] = None
        self.title = ""
        self.description = ""
        self.contract = None
        self.tag = ""

    def on_title_changed(self, e):
        self.title = e.control.value

    def on_description_changed(self, e):
        self.description = e.control.value

    def on_tag_changed(self, e):
        self.tag = e.control.value

    def clear_title_error(self, e):
        if self.title_field.error_text:
            self.title_field.error_text = None
            self.update_self()

    def clear_description_error(self, e):
        if self.description_field.error_text:
            self.description_field.error_text = None
            self.update_self()

    # LOADING DATA
    def did_mount(self):
        self.mounted = True
        self.show_progress_bar_disable_action()
        result: IntentResult = self.intent.get_project_by_id(self.project_id)
        if result.was_intent_successful:
            self.project = result.data
            self.set_project_fields()
        else:
            self.show_snack(result.error_msg, True)
        self.enable_action_remove_progress_bar()
        self.update_self()

    def show_progress_bar_disable_action(self):
        self.loading_indicator.visible = True
        self.submit_btn.disabled = True

    def enable_action_remove_progress_bar(self):
        self.loading_indicator.visible = False
        self.submit_btn.disabled = False

    def set_project_fields(self):
        """if user is editing a project
        set the data of the project as form values
        """
        if not self.project:
            return

        self.title = self.project.title
        self.title_field.value = self.title
        self.description = self.project.description
        self.description_field.value = self.description
        self.tag = self.project.tag
        self.tag_field.value = self.tag
        self.start_date_field.set_date(self.project.start_date)
        self.end_date_field.set_date(self.project.end_date)
        self.contract_title_view.value = f"Contract {self.project.contract.title}"
        self.client_title_view.value = f"Client {self.project.contract.client.name}"

    def on_save(self, e):
        if not self.title:
            self.title_field.error_text = "Project title is required"
            self.update_self()
            return

        if not self.description:
            self.description_field.error_text = "Project description is required"
            self.update_self()
            return

        start_date_value = self.start_date_field.get_date()
        if start_date_value is None:
            self.show_snack("Please specify the start date", True)
            return

        end_date_value = self.end_date_field.get_date()
        if end_date_value is None:
            self.show_snack("Please specify the end date", True)
            return

        if start_date_value > end_date_value:
            self.show_snack(
                "The end date of the project cannot be before the start date", True
            )
            return

        self.show_progress_bar_disable_action()
        result: IntentResult = self.intent.save_project(
            title=self.title,
            description=self.description,
            start_date=start_date_value,
            end_date=end_date_value,
            unique_tag=self.tag,
            contract=self.project.contract,
            project=self.project,
        )

        msg = (
            "Updated project successfully"
            if result.was_intent_successful
            else result.error_msg
        )
        isError = not result.was_intent_successful
        self.enable_action_remove_progress_bar()
        self.show_snack(msg, isError)
        if result.was_intent_successful:
            self.on_navigate_back()

    def build(self):
        self.title_field = views.get_std_txt_field(
            label="Title",
            hint="Project's title",
            on_change=self.on_title_changed,
            on_focus=self.clear_title_error,
        )
        self.description_field = views.get_std_multiline_field(
            label="Description",
            hint="Project's description",
            on_change=self.on_description_changed,
            on_focus=self.clear_description_error,
        )
        self.tag_field = views.get_std_txt_field(
            label="Tag",
            hint="a unique #tag for the project",
            on_change=self.on_tag_changed,
        )
        self.start_date_field = views.DateSelector(label="Start Date")
        self.end_date_field = views.DateSelector(label="End Date")
        self.submit_btn = views.get_primary_btn(
            label="Create Project" if self.project_id is None else "Update Project",
            on_click=self.on_save,
        )
        self.contract_title_view = Text(size=fonts.BODY_1_SIZE, color=colors.GRAY_COLOR)
        self.client_title_view = Text(size=fonts.BODY_1_SIZE, color=colors.GRAY_COLOR)
        view = Container(
            expand=True,
            padding=padding.all(dimens.SPACE_MD),
            margin=margin.symmetric(vertical=dimens.SPACE_MD),
            content=Card(
                expand=True,
                content=Container(
                    Column(
                        expand=True,
                        controls=[
                            Row(
                                controls=[
                                    IconButton(
                                        icon=icons.CHEVRON_LEFT_ROUNDED,
                                        on_click=self.on_navigate_back,
                                    ),
                                    views.get_headline_with_subtitle(
                                        title="Edit Project",
                                        subtitle="Update project",
                                    ),
                                ]
                            ),
                            self.loading_indicator,
                            views.mdSpace,
                            self.contract_title_view,
                            self.client_title_view,
                            views.smSpace,
                            self.title_field,
                            views.smSpace,
                            self.description_field,
                            views.smSpace,
                            self.tag_field,
                            views.mdSpace,
                            self.start_date_field,
                            views.mdSpace,
                            self.end_date_field,
                            views.mdSpace,
                            self.submit_btn,
                        ],
                    ),
                    padding=padding.all(dimens.SPACE_MD),
                    width=dimens.MIN_WINDOW_WIDTH,
                ),
            ),
        )

        return view

    def will_unmount(self):
        self.mounted = False


class CreateProjectScreen(TuttleView, UserControl):
    def __init__(self, params):
        super().__init__(params)
        self.horizontal_alignment_in_parent = utils.CENTER_ALIGNMENT
        self.intent = ProjectsIntent()

        self.contracts_map = {}
        self.loading_indicator = views.horizontal_progress
        self.title = ""
        self.description = ""
        self.tag = ""
        self.contract: Optional[Contract] = None
        self.start_date = None
        self.end_date = None

    def on_title_changed(self, e):
        self.title = e.control.value

    def on_description_changed(self, e):
        self.description = e.control.value

    def on_tag_changed(self, e):
        self.tag = e.control.value

    def add_tag_to_dropdown_item_id(self, id, value):
        """given id and value, prepends a # symbol and returns as str"""
        return f"#{id} {value}"

    def get_contracts_as_list(self):
        """transforms a map of id-contract_desc to a list for dropdown options"""
        contracts = []
        for key in self.contracts_map:
            contracts.append(
                self.add_tag_to_dropdown_item_id(
                    id=key, value=self.contracts_map[key].title
                )
            )
        return contracts

    def get_id_from_dropdown_selection(self, selected: str):
        id = ""
        for c in selected:
            if c == "#":
                continue
            if c == " ":
                break
            id = id + c
        return id

    def on_contract_selected(self, e):
        # parse selected value to extract id
        contract_id = self.get_id_from_dropdown_selection(selected=e.control.value)
        if int(contract_id) in self.contracts_map:
            self.contract = self.contracts_map[int(contract_id)]
        if self.contracts_field.error_text:
            self.contracts_field.error_text = None
            self.update_self()

    def clear_title_error(self, e):
        if self.title_field.error_text:
            self.title_field.error_text = None
            self.update_self()

    def clear_description_error(self, e):
        if self.description_field.error_text:
            self.description_field.error_text = None
            self.update_self()

    # LOADING DATA
    def did_mount(self):
        self.mounted = True
        self.show_progress_bar_disable_action()
        self.reload_load_contracts()
        self.enable_action_remove_progress_bar()
        self.update_self()

    def show_progress_bar_disable_action(self):
        self.loading_indicator.visible = True
        self.submit_btn.disabled = True

    def enable_action_remove_progress_bar(self):
        self.loading_indicator.visible = False
        self.submit_btn.disabled = False

    def reload_load_contracts(
        self,
    ):
        self.contracts_map = self.intent.get_all_contracts_as_map()
        self.contracts_field.error_text = (
            "Please create a new contract" if len(self.contracts_map) == 0 else None
        )
        views.update_dropdown_items(self.contracts_field, self.get_contracts_as_list())

    def on_add_contract(self, e):
        # todo confirm? before re routing
        self.navigate_to_route(res_utils.CONTRACT_CREATOR_SCREEN_ROUTE)

    def on_save(self, e):
        if not self.title:
            self.title_field.error_text = "Project title is required"
            self.update_self()
            return

        if not self.description:
            self.description_field.error_text = "Project description is required"
            self.update_self()
            return

        self.start_date = self.start_date_field.get_date()
        if self.start_date is None:
            self.show_snack("Please specify the start date", True)
            return

        self.end_date = self.end_date_field.get_date()
        if self.end_date is None:
            self.show_snack("Please specify the end date", True)
            return

        if self.start_date > self.end_date:
            self.show_snack(
                "The end date of the project cannot be before the start date", True
            )
            return

        if self.contract is None:
            self.contracts_field.error_text = "Please specify the contract"
            self.update_self()
            return

        self.show_progress_bar_disable_action()
        result: IntentResult = self.intent.save_project(
            title=self.title,
            description=self.description,
            start_date=self.start_date,
            end_date=self.end_date,
            unique_tag=self.tag,
            contract=self.contract,
        )
        successMsg = "New project created successfully"
        msg = successMsg if result.was_intent_successful else result.error_msg
        isError = not result.was_intent_successful
        self.enable_action_remove_progress_bar()
        self.show_snack(msg, isError)
        if result.was_intent_successful:
            # re -route back
            self.on_navigate_back()

    def build(self):
        self.title_field = views.get_std_txt_field(
            label="Title",
            hint="Project's title",
            on_change=self.on_title_changed,
            on_focus=self.clear_title_error,
        )
        self.description_field = views.get_std_multiline_field(
            label="Description",
            hint="Project's description",
            on_change=self.on_description_changed,
            on_focus=self.clear_description_error,
        )
        self.tag_field = views.get_std_txt_field(
            label="Tag",
            hint="an optional tag",
            on_change=self.on_tag_changed,
        )

        self.contracts_field = views.get_dropdown(
            label="Contract",
            on_change=self.on_contract_selected,
            items=self.get_contracts_as_list(),
        )
        self.start_date_field = views.DateSelector(label="Start Date")
        self.end_date_field = views.DateSelector(label="End Date")
        self.submit_btn = views.get_primary_btn(
            label="Create Project",
            on_click=self.on_save,
        )

        self.contractsEditor = Row(
            alignment=utils.SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=utils.CENTER_ALIGNMENT,
            spacing=dimens.SPACE_STD,
            controls=[
                self.contracts_field,
                IconButton(
                    icon=icons.ADD_CIRCLE_OUTLINE,
                    on_click=self.on_add_contract,
                ),
            ],
        )

        """used to display contract id
        for when editing the project"""
        self.contract_title_view = Text(
            size=fonts.BODY_1_SIZE, color=colors.GRAY_COLOR, visible=False
        )
        view = Container(
            expand=True,
            padding=padding.all(dimens.SPACE_MD),
            margin=margin.symmetric(vertical=dimens.SPACE_MD),
            content=Card(
                expand=True,
                content=Container(
                    Column(
                        expand=True,
                        controls=[
                            Row(
                                controls=[
                                    IconButton(
                                        icon=icons.CHEVRON_LEFT_ROUNDED,
                                        on_click=self.on_navigate_back,
                                    ),
                                    views.get_headline_with_subtitle(
                                        title="New Project",
                                        subtitle="Create a new project",
                                    ),
                                ]
                            ),
                            self.loading_indicator,
                            views.mdSpace,
                            self.title_field,
                            views.smSpace,
                            self.description_field,
                            views.smSpace,
                            self.contractsEditor,
                            self.contract_title_view,
                            views.smSpace,
                            self.tag_field,
                            views.mdSpace,
                            self.start_date_field,
                            views.mdSpace,
                            self.end_date_field,
                            views.mdSpace,
                            self.submit_btn,
                        ],
                    ),
                    padding=padding.all(dimens.SPACE_MD),
                    width=dimens.MIN_WINDOW_WIDTH,
                ),
            ),
        )

        return view

    def will_unmount(self):
        self.mounted = False
