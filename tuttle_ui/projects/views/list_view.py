from flet import (
    Column,
    Container,
    GridView,
    ResponsiveRow,
    Text,
    UserControl,
)

from core.constants_and_enums import ALWAYS_SCROLL
from core.abstractions import TuttleView
from core.views import get_headline_txt, horizontal_progress, mdSpace

from projects.intent_impl import ProjectsIntentImpl
from res.colors import ERROR_COLOR
from res.dimens import SPACE_MD, SPACE_STD
from res.fonts import HEADLINE_4_SIZE
from res.strings import MY_PROJECTS, NO_PROJECTS_ADDED
from res.utils import PROJECT_DETAILS_SCREEN_ROUTE

from .project_card import ProjectCard
from .project_filters import ProjectFiltersView, ProjectStates


class ProjectsListView(TuttleView, UserControl):
    def __init__(self, navigate_to_route, show_snack, dialog_controller, local_storage):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = ProjectsIntentImpl(local_storage=local_storage)
        self.loading_indicator = horizontal_progress
        self.no_projects_control = Text(
            value=NO_PROJECTS_ADDED, color=ERROR_COLOR, visible=False
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt=MY_PROJECTS, size=HEADLINE_4_SIZE),
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
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.projects_to_display = {}

    def load_all_projects(self):
        self.projects_to_display = self.intent_handler.get_all_projects_as_map()

    def display_currently_filtered_projects(self):
        self.projects_container.controls.clear()
        for key in self.projects_to_display:
            project = self.projects_to_display[key]
            projectCard = ProjectCard(
                project=project, onClickView=self.on_view_project_clicked
            )
            self.projects_container.controls.append(projectCard)

    def on_view_project_clicked(self, projectId: str):
        self.navigate_to_route(PROJECT_DETAILS_SCREEN_ROUTE, projectId)

    def on_filter_projects(self, filterByState: ProjectStates):
        if filterByState.value == ProjectStates.ACTIVE.value:
            self.projects_to_display = self.intent_handler.get_active_projects()
        elif filterByState.value == ProjectStates.UPCOMING.value:
            self.projects_to_display = self.intent_handler.get_upcoming_projects()
        elif filterByState.value == ProjectStates.COMPLETED.value:
            self.projects_to_display = self.intent_handler.get_completed_projects()
        else:
            self.projects_to_display = self.intent_handler.get_all_projects_as_map()
        self.display_currently_filtered_projects()
        self.update()

    def show_no_projects(self):
        self.no_projects_control.visible = True

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.load_all_projects()
            count = len(self.projects_to_display)
            self.loading_indicator.visible = False
            if count == 0:
                self.show_no_projects()
            else:
                self.display_currently_filtered_projects()
            if self.mounted:
                self.update()
        except Exception as e:
            # logger
            print(f"exception raised @projects.did_mount {e}")

    def build(self):
        return Column(
            controls=[
                self.title_control,
                mdSpace,
                ProjectFiltersView(onStateChanged=self.on_filter_projects),
                mdSpace,
                Container(self.projects_container, expand=True),
            ]
        )

    def will_unmount(self):
        self.mounted = False
