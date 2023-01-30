from typing import Callable, Optional

from enum import Enum

from flet import (
    ButtonStyle,
    Card,
    Column,
    Container,
    ElevatedButton,
    FontWeight,
    GridView,
    Icon,
    IconButton,
    ListTile,
    ResponsiveRow,
    Row,
    TextButton,
    UserControl,
    border_radius,
    icons,
    margin,
    padding,
)

from clients.view import ClientViewPopUp
from core import utils, views
from core.abstractions import TView, TViewParams
from core.intent_result import IntentResult
from projects.intent import ProjectsIntent
from res import colors, dimens, fonts, res_utils

from tuttle.model import Contract, Project


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
        """Builds the project card"""
        _contract_title = "Unknown contract"
        if self.project.contract:
            _contract_title = self.project.contract.title
        _client_title = "Unknown client"
        if self.project.client:
            _client_title = self.project.client.name
        self.project_info_container.controls = [
            ListTile(
                leading=Icon(
                    utils.TuttleComponentIcons.project_icon,
                    size=dimens.ICON_SIZE,
                ),
                title=views.TBodyText(self.project.title),
                subtitle=views.TBodyText(
                    f"{self.project.tag}",
                    color=colors.GRAY_COLOR,
                    weight=FontWeight.BOLD,
                ),
                trailing=views.TContextMenu(
                    on_click_view=lambda e: self.on_view_details_clicked(
                        self.project.id
                    ),
                    on_click_delete=lambda e: self.on_delete_clicked(self.project.id),
                    on_click_edit=lambda e: self.on_edit_clicked(self.project.id),
                ),
                on_click=lambda e: self.on_view_details_clicked(self.project.id),
            ),
            views.Spacer(md_space=True),
            ResponsiveRow(
                controls=[
                    views.TBodyText(
                        txt="Brief Description",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    views.TBodyText(
                        txt=self.project.get_brief_description(),
                        col={"xs": "12"},
                    ),
                ],
                spacing=dimens.SPACE_XS,
                run_spacing=0,
                vertical_alignment=utils.CENTER_ALIGNMENT,
            ),
            views.Spacer(md_space=True),
            ResponsiveRow(
                controls=[
                    views.TBodyText(
                        txt="Client",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        views.TBodyText(
                            txt=_client_title,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=utils.START_ALIGNMENT,
                vertical_alignment=utils.START_ALIGNMENT,
                spacing=dimens.SPACE_XS,
                run_spacing=0,
            ),
            views.Spacer(md_space=True),
            ResponsiveRow(
                controls=[
                    views.TBodyText(
                        txt="Contract",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        views.TBodyText(
                            txt=_contract_title,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=utils.START_ALIGNMENT,
                vertical_alignment=utils.START_ALIGNMENT,
                spacing=dimens.SPACE_XS,
                run_spacing=0,
            ),
            views.Spacer(md_space=True),
            ResponsiveRow(
                controls=[
                    views.TBodyText(
                        txt="Start date",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        views.TBodyText(
                            txt=self.project.start_date.strftime("%d/%m/%Y")
                            if self.project.start_date
                            else "",
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=utils.START_ALIGNMENT,
                vertical_alignment=utils.START_ALIGNMENT,
                spacing=dimens.SPACE_XS,
                run_spacing=0,
            ),
            views.Spacer(md_space=True),
            ResponsiveRow(
                controls=[
                    views.TBodyText(
                        txt="End date",
                        color=colors.GRAY_COLOR,
                        size=fonts.BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        views.TBodyText(
                            txt=self.project.end_date.strftime("%d/%m/%Y")
                            if self.project.end_date
                            else "-",
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
            views.Spacer(md_space=True),
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
    """Project states"""

    ALL = 1
    ACTIVE = 2
    COMPLETED = 3
    UPCOMING = 4


def get_filter_button_label(state: ProjectStates):
    """returns the label for the filter button"""
    if state.value == ProjectStates.ACTIVE.value:
        return "Active"
    elif state.value == ProjectStates.UPCOMING.value:
        return "Upcoming"
    elif state.value == ProjectStates.COMPLETED.value:
        return "Completed"
    else:
        return "All"


def get_filter_button_tooltip(state: ProjectStates):
    """returns the tooltip for the filter button"""
    if state.value == ProjectStates.ACTIVE.value:
        return "Not completed and not due."
    elif state.value == ProjectStates.UPCOMING.value:
        return "Scheduled for the future."
    elif state.value == ProjectStates.COMPLETED.value:
        return "Marked as completed."
    else:
        return "All projects."


class ProjectFiltersView(UserControl):
    """Create and Handles projects view filtering buttons"""

    def __init__(self, onStateChanged: Callable[[ProjectStates], None]):
        super().__init__()
        self.currentState = ProjectStates.ALL
        self.stateTofilterButtonsMap = {}
        self.onStateChangedCallback = onStateChanged

    def filter_button(
        self,
        state: ProjectStates,
        label: str,
        onClick: Callable[[ProjectStates], None],
        tooltip: str,
    ):
        """creates a filter button for project status"""
        button = ElevatedButton(
            text=label,
            col={"xs": 6, "sm": 3, "lg": 2},
            on_click=lambda e: onClick(state),
            height=dimens.CLICKABLE_PILL_HEIGHT,
            color=colors.PRIMARY_COLOR
            if state == self.currentState
            else colors.GRAY_COLOR,
            tooltip=tooltip,
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

    def set_filter_buttons(self):
        """sets the filter buttons for each project state"""
        for state in ProjectStates:
            button = self.filter_button(
                label=get_filter_button_label(state),
                state=state,
                onClick=self.on_filter_button_clicked,
                tooltip=get_filter_button_tooltip(state),
            )
            self.stateTofilterButtonsMap[state] = button

    def build(self):
        """builds the filter buttons"""
        if len(self.stateTofilterButtonsMap) == 0:
            # set the buttons
            self.set_filter_buttons()

        self.filters = ResponsiveRow(
            controls=list(self.stateTofilterButtonsMap.values())
        )
        return self.filters


class ViewProjectScreen(TView, UserControl):
    """View project screen"""

    def __init__(
        self,
        params: TViewParams,
        project_id: str,
    ):
        super().__init__(params)
        self.intent = ProjectsIntent()
        self.project_id = project_id
        self.loading_indicator = views.TProgressBar()
        self.project: Optional[Project] = None
        self.pop_up_handler = None

    def display_project_data(self):
        """displays the project data on the screen"""
        has_contract = True if self.project.contract else False
        has_client = True if has_contract and self.project.contract.client else False

        self.project_title_control.value = self.project.title
        self.client_control.value = (
            f"Client {self.project.contract.client.name}"
            if has_client
            else "Client not specified"
        )
        self.contract_control.value = (
            f"Contract Title: {self.project.contract.title}"
            if has_contract
            else "Contract not specified"
        )
        self.project_description_control.value = self.project.description
        self.project_start_date_control.value = f"Start Date: {self.project.start_date}"
        self.project_end_date_control.value = f"End Date: {self.project.end_date}"
        _status = self.project.get_status(default="")
        if _status:
            self.project_status_control.value = f"Status {_status}"
        self.project_tagline_control.value = f"{self.project.tag}"
        is_project_completed = self.project.is_completed
        self.toggle_complete_status_btn.icon = (
            icons.RADIO_BUTTON_CHECKED_OUTLINED
            if is_project_completed
            else icons.RADIO_BUTTON_UNCHECKED_OUTLINED
        )
        self.toggle_complete_status_btn.tooltip = (
            "Mark as incomplete" if is_project_completed else "Mark as complete"
        )

    def on_view_client_clicked(self, e):
        """opens the client view pop up when the client button is clicked"""
        if not self.project or not self.project.client:
            return
        if self.pop_up_handler:
            self.pop_up_handler.close_dialog()
        self.pop_up_handler = ClientViewPopUp(
            dialog_controller=self.dialog_controller, client=self.project.client
        )
        self.pop_up_handler.open_dialog()

    def on_view_contract_clicked(self, e):
        """redirects to the contract view screen when the contract button is clicked"""
        if not self.project or not self.project.contract:
            return
        self.navigate_to_route(
            res_utils.CONTRACT_DETAILS_SCREEN_ROUTE, self.project.contract.id
        )

    def toggle_complete_status(self, e):
        """toggles the project complete status"""
        if self.project is None:
            return  # project is not loaded yet
        result: IntentResult = self.intent.toggle_project_completed_status(self.project)
        is_error = not result.was_intent_successful
        msg = "Updated project." if not is_error else result.error_msg
        self.show_snack(msg, is_error)
        if not is_error:
            self.project = result.data
            self.display_project_data()
            self.update_self()  # update the view

    def on_edit_clicked(self, e):
        """redirects to the project editor screen when the edit button is clicked"""
        if self.project is None:
            # project is not loaded yet
            return
        self.navigate_to_route(res_utils.PROJECT_EDITOR_SCREEN_ROUTE, self.project.id)

    def on_delete_clicked(self, e):
        """Called when the user clicks the delete button"""
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
        """Called when the user confirms the deletion of a project"""
        result = self.intent.delete_project_by_id(project_id)
        is_err = not result.was_intent_successful
        msg = result.error_msg if is_err else "Project deleted!"
        self.show_snack(msg, is_err)
        if not is_err:
            # go back, project has been deleted
            self.navigate_back()

    def build(self):
        """Called when page is built"""
        self.edit_project_btn = IconButton(
            icon=icons.EDIT_OUTLINED,
            tooltip="Edit project",
            on_click=self.on_edit_clicked,
            icon_size=dimens.ICON_SIZE,
        )

        self.toggle_complete_status_btn = IconButton(
            icon=icons.RADIO_BUTTON_UNCHECKED_OUTLINED,
            icon_color=colors.PRIMARY_COLOR,
            tooltip="Mark as complete",
            icon_size=dimens.ICON_SIZE,
            on_click=self.toggle_complete_status,
        )
        self.delete_project_btn = IconButton(
            icon=icons.DELETE_OUTLINE_ROUNDED,
            icon_color=colors.ERROR_COLOR,
            tooltip="Delete project",
            icon_size=dimens.ICON_SIZE,
            on_click=self.on_delete_clicked,
        )

        self.project_title_control = views.THeading()

        self.client_control = views.TSubHeading(
            color=colors.GRAY_COLOR,
        )
        self.contract_control = views.TSubHeading(
            color=colors.GRAY_COLOR,
        )
        self.project_description_control = views.TBodyText(
            align=utils.TXT_ALIGN_JUSTIFY,
        )

        self.project_start_date_control = views.TSubHeading(
            size=fonts.BUTTON_SIZE,
            color=colors.GRAY_COLOR,
        )
        self.project_end_date_control = views.TSubHeading(
            size=fonts.BUTTON_SIZE,
            color=colors.GRAY_COLOR,
        )

        self.project_status_control = views.TSubHeading(
            size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR
        )
        self.project_tagline_control = views.TSubHeading(
            size=fonts.BUTTON_SIZE, color=colors.PRIMARY_COLOR
        )

        page_view = Row(
            [
                Container(
                    padding=padding.all(dimens.SPACE_STD),
                    width=int(dimens.MIN_WINDOW_WIDTH * 0.3),
                    content=Column(
                        controls=[
                            IconButton(
                                icon=icons.KEYBOARD_ARROW_LEFT,
                                on_click=self.navigate_back,
                                icon_size=dimens.ICON_SIZE,
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
                                    Icon(
                                        icons.WORK_ROUNDED,
                                        size=dimens.ICON_SIZE,
                                    ),
                                    Column(
                                        expand=True,
                                        spacing=0,
                                        run_spacing=0,
                                        controls=[
                                            Row(
                                                vertical_alignment=utils.CENTER_ALIGNMENT,
                                                alignment=utils.SPACE_BETWEEN_ALIGNMENT,
                                                controls=[
                                                    views.THeading(
                                                        "Project",
                                                        size=fonts.HEADLINE_4_SIZE,
                                                        color=colors.PRIMARY_COLOR,
                                                    ),
                                                    Row(
                                                        vertical_alignment=utils.CENTER_ALIGNMENT,
                                                        alignment=utils.SPACE_BETWEEN_ALIGNMENT,
                                                        spacing=dimens.SPACE_STD,
                                                        run_spacing=dimens.SPACE_STD,
                                                        controls=[
                                                            self.edit_project_btn,
                                                            self.toggle_complete_status_btn,
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
                            views.Spacer(md_space=True),
                            views.TSubHeading(
                                subtitle="Project Description",
                            ),
                            self.project_description_control,
                            self.project_start_date_control,
                            self.project_end_date_control,
                            views.Spacer(md_space=True),
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

    def did_mount(self):
        """called when the view is mounted"""
        self.reload_data()

    def on_resume_after_back_pressed(self):
        """called when the view is resumed after back pressed"""
        self.reload_data()

    def reload_data(self):
        """reloads data whem the view is first mounted or resumed"""
        self.mounted = True
        result: IntentResult = self.intent.get_project_by_id(self.project_id)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.project = result.data
            self.display_project_data()
        self.loading_indicator.visible = False
        self.update_self()

    def will_unmount(self):
        """called when the view is unmounted"""
        self.mounted = False
        if self.pop_up_handler:
            self.pop_up_handler.dimiss_open_dialogs()


class ProjectsListView(TView, UserControl):
    """View for displaying a list of projects"""

    def __init__(self, params):
        super().__init__(params)
        self.intent = ProjectsIntent()
        self.loading_indicator = views.TProgressBar()
        self.no_projects_control = views.TBodyText(
            txt="You have not added any projects yet.",
            color=colors.ERROR_COLOR,
            show=False,
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.THeading(title="My Projects", size=fonts.HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.no_projects_control,
                    ],
                )
            ]
        )
        self.projects_container = GridView(
            expand=False,
            max_extent=560,
            child_aspect_ratio=1.0,
            spacing=dimens.SPACE_STD,
            run_spacing=dimens.SPACE_MD,
        )
        self.projects_to_display = {}
        self.dialog = None

    def display_currently_filtered_projects(self):
        """Display the projects that according to the current filter"""
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
        """Called when view details button is clicked on a project card"""
        self.navigate_to_route(res_utils.PROJECT_DETAILS_SCREEN_ROUTE, project_id)

    def on_delete_project_clicked(self, project_id: str):
        """Called when delete button is clicked on a project card"""
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

    def on_delete_confirmed(self, project_id: str):
        """Called when the user confirms the delete action"""
        self.loading_indicator.visible = True
        self.update_self()
        result = self.intent.delete_project_by_id(project_id)
        is_err = not result.was_intent_successful
        if not is_err:
            if int(project_id) in self.projects_to_display:
                # remove deleted project from displayed projects
                del self.projects_to_display[int(project_id)]
            # reload displayed projects
            self.display_currently_filtered_projects()
        msg = result.error_msg if is_err else "Project deleted!"
        self.show_snack(msg, is_err)
        self.loading_indicator.visible = False
        self.update_self()

    def on_edit_project_clicked(self, project_id: str):
        """Called when edit button is clicked on a project card,redirects to project editor"""
        self.navigate_to_route(res_utils.PROJECT_EDITOR_SCREEN_ROUTE, project_id)

    def on_filter_projects(self, filterByState: ProjectStates):
        """Called when the user selects a filter option"""
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

    def did_mount(self):
        """called when the view is mounted"""
        self.reload_data()

    def parent_intent_listener(self, intent: str, data: any):
        """Called when the parent view sends an intent"""
        if intent == res_utils.RELOAD_INTENT:
            self.reload_data()

    def reload_data(self):
        """reloads data displayed when view is mounted or when parent view sends a reload intent"""
        self.mounted = True
        self.loading_indicator.visible = True
        self.projects_to_display = self.intent.get_all_projects_as_map()
        count = len(self.projects_to_display)
        self.loading_indicator.visible = False
        if count == 0:
            # Show the no projects message
            self.no_projects_control.visible = True
            self.projects_container.controls.clear()
        else:
            self.no_projects_control.visible = False
            self.display_currently_filtered_projects()
        self.update_self()

    def build(self):
        """Builds the view"""
        return Column(
            controls=[
                self.title_control,
                views.Spacer(md_space=True),
                ProjectFiltersView(onStateChanged=self.on_filter_projects),
                views.Spacer(md_space=True),
                Container(self.projects_container, expand=True),
            ]
        )

    def will_unmount(self):
        """Called when the view is unmounted"""
        self.mounted = False


class ProjectEditorScreen(TView, UserControl):
    """Displays a form for creating or updating a project"""

    def __init__(
        self,
        params: TViewParams,
        project_id_if_editing: Optional[str] = None,
    ):
        super().__init__(params)
        self.horizontal_alignment_in_parent = utils.CENTER_ALIGNMENT
        self.intent = ProjectsIntent()
        self.project_id_if_editing = project_id_if_editing
        self.old_project_if_editing: Optional[Project] = None
        self.contracts_map = {}
        self.loading_indicator = views.TProgressBar()
        self.title = ""
        self.description = ""
        self.tag = ""
        self.contract: Optional[Contract] = None
        self.start_date = None
        self.end_date = None

    def on_title_changed(self, e):
        """Called when the title input changes"""
        self.title = e.control.value

    def on_description_changed(self, e):
        """Called when the description input changes"""
        self.description = e.control.value

    def on_tag_changed(self, e):
        """Called when the tag input changes"""
        self.tag = e.control.value

    def add_tag_to_dropdown_item_id(self, id, value):
        """given id and value, prepends a # symbol and returns as str"""
        return f"#{id} {value}"

    def get_id_from_dropdown_selection(self, selected: str):
        """given a dropdown selection, extracts the id from the selection"""
        _id = ""
        for c in selected:
            if c == "#":
                continue
            if c == " ":
                break
            _id = _id + c
        return _id

    def get_contracts_as_list(self):
        """transforms a map of id - to  - contract to a list for dropdown options"""
        contracts = []
        for key in self.contracts_map:
            contracts.append(
                self.add_tag_to_dropdown_item_id(
                    id=key, value=self.contracts_map[key].title
                )
            )
        return contracts

    def on_contract_selected(self, e):
        """Called when a contract is selected from the dropdown"""
        contract_id = self.get_id_from_dropdown_selection(selected=e.control.value)
        if int(contract_id) in self.contracts_map:
            self.contract = self.contracts_map[int(contract_id)]
        self.contracts_field.update_error_txt()
        self.update_self()

    def clear_title_error(self, e):
        """Called when the title input is focused"""
        if self.title_field.error_text:
            self.title_field.error_text = None
            self.update_self()

    def clear_description_error(self, e):
        """Called when the description input is focused"""
        if self.description_field.error_text:
            self.description_field.error_text = None
            self.update_self()

    def toggle_progress_indicator(self, is_action_ongoing: bool):
        """Toggles the progress indicator visibility and disables / enables the submit button"""
        self.loading_indicator.visible = is_action_ongoing
        self.submit_btn.disabled = is_action_ongoing

    def load_project_for_editing(self):
        """Loads the project being edited if a project id was passed to the view"""
        if not self.project_id_if_editing:
            return  # user is not updating a project

        result = self.intent.get_project_by_id(self.project_id_if_editing)
        if not result.was_intent_successful or not result.data:
            self.show_snack(result.error_msg)
            return  # error loading project
        self.old_project_if_editing = result.data
        self.set_form_values()  # set form values

    def set_form_values(self):
        """Sets form data with info of project being edited"""
        self.title_field.value = self.title = self.old_project_if_editing.title
        self.description_field.value = (
            self.description
        ) = self.old_project_if_editing.description
        self.start_date = self.old_project_if_editing.start_date
        self.start_date_field.set_date(self.start_date)
        self.end_date = self.old_project_if_editing.end_date
        self.end_date_field.set_date(self.end_date)
        self.tag_field.value = self.tag = self.old_project_if_editing.tag
        self.contract = self.old_project_if_editing.contract
        if self.contract:
            contract_as_list_item = self.add_tag_to_dropdown_item_id(
                id=self.contract.id, value=self.contract.title
            )
            self.contracts_field.update_value(contract_as_list_item)
        self.form_title.value = "Edit Project"
        self.submit_btn.text = "Update Project"

    def reload_contracts(
        self,
    ):
        """Reloads the contracts for the dropdown field"""
        self.contracts_map = self.intent.get_all_contracts_as_map_intent()
        self.contracts_field.error_text = (
            "Please create a new contract" if len(self.contracts_map) == 0 else None
        )
        self.contracts_field.update_dropdown_items(self.get_contracts_as_list())

    def on_add_contract(self, e):
        """Called when the add contract button is clicked, redirects to the contract editor screen"""
        self.navigate_to_route(res_utils.CONTRACT_EDITOR_SCREEN_ROUTE)

    def on_save(self, e):
        """Called when the save button is clicked, validates the form and saves the project"""
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

        if self.tag is None:
            self.tag_field.error_text = "The project must have a tag."
            self.update_self()
            return

        self.toggle_progress_indicator(is_action_ongoing=True)
        result: IntentResult = self.intent.save_project(
            title=self.title,
            description=self.description,
            start_date=self.start_date,
            end_date=self.end_date,
            unique_tag=self.tag,
            contract=self.contract,
            project=self.old_project_if_editing,
        )
        successMsg = (
            "Changes saved"
            if self.old_project_if_editing
            else "New project created successfully"
        )
        msg = successMsg if result.was_intent_successful else result.error_msg
        isError = not result.was_intent_successful
        self.toggle_progress_indicator(is_action_ongoing=False)
        self.show_snack(msg, isError)
        if result.was_intent_successful:
            # re -route back
            self.navigate_back()

    def build(self):
        """Builds the view"""
        self.title_field = views.TTextField(
            label="Title",
            hint="A short, unique title",
            on_change=self.on_title_changed,
            on_focus=self.clear_title_error,
        )
        self.description_field = views.TMultilineField(
            label="Description",
            hint="A longer description of the project",
            on_change=self.on_description_changed,
            on_focus=self.clear_description_error,
        )
        self.tag_field = views.TTextField(
            label="Tag",
            hint="A unique tag",
            on_change=self.on_tag_changed,
        )

        self.contracts_field = views.TDropDown(
            label="Contract",
            on_change=self.on_contract_selected,
            items=self.get_contracts_as_list(),
        )
        self.start_date_field = views.DateSelector(label="Start Date")
        self.end_date_field = views.DateSelector(label="End Date")
        self.contract_editor = Row(
            alignment=utils.SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=utils.CENTER_ALIGNMENT,
            spacing=dimens.SPACE_STD,
            controls=[
                self.contracts_field,
                IconButton(
                    icon=icons.ADD_CIRCLE_OUTLINE,
                    on_click=self.on_add_contract,
                    icon_size=dimens.ICON_SIZE,
                ),
            ],
        )

        self.form_title = views.THeading(
            title="New Project",
        )
        self.submit_btn = views.TPrimaryButton(
            label="Create Project",
            on_click=self.on_save,
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
                                        on_click=self.navigate_back,
                                        icon_size=dimens.ICON_SIZE,
                                    ),
                                    self.form_title,
                                ]
                            ),
                            self.loading_indicator,
                            views.Spacer(md_space=True),
                            self.title_field,
                            views.Spacer(),
                            self.description_field,
                            views.Spacer(),
                            self.contract_editor,
                            views.Spacer(),
                            self.tag_field,
                            views.Spacer(lg_space=True),
                            self.start_date_field,
                            views.Spacer(lg_space=True),
                            self.end_date_field,
                            views.Spacer(lg_space=True),
                            self.submit_btn,
                        ],
                    ),
                    padding=padding.all(dimens.SPACE_MD),
                    width=dimens.MIN_WINDOW_WIDTH,
                ),
            ),
        )

        return view

    def did_mount(self):
        """Called when the view is mounted"""
        self.mounted = True
        self.initialize_data()

    def on_resume_after_back_pressed(self):
        """Called when the view is resumed from another screen by back press"""
        self.initialize_data(skip_project_reload=True)

    def initialize_data(self, skip_project_reload: bool = False):
        """Initializes the data for the view"""
        self.toggle_progress_indicator(is_action_ongoing=True)
        if not skip_project_reload:
            self.load_project_for_editing()
        self.reload_contracts()
        self.toggle_progress_indicator(is_action_ongoing=False)
        self.update_self()

    def will_unmount(self):
        """Called when the view is unmounted"""
        self.mounted = False
