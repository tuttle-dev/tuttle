import typing
from typing import Callable

from flet import Card, Column, Container, GridView, ResponsiveRow, Text, padding

from core.abstractions.local_cache import LocalCache
from core.ui.components.progress.horizontal_progress_bars import PRIMARY_LIGHT_PROGRESS
from core.ui.components.spacers import mdSpace
from core.ui.components.text.headlines import get_headline_txt
from projects.abstractions.projects_destination_view import ProjectDestinationView
from res.colors import BLACK_COLOR, ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_MD, SPACE_STD
from res.strings import MY_PROJECTS, NO_PROJECTS_ADDED

from .components.project_card import ProjectCard
from .components.projects_view_filters import ProjectFiltersView, ProjectStates


class ProjectsDestinationViewImpl(ProjectDestinationView):
    def __init__(
        self,
        localCacheHandler: LocalCache,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
    ):
        super().__init__(
            localCacheHandler=localCacheHandler,
            onChangeRouteCallback=onChangeRouteCallback,
        )
        self.progressBar = PRIMARY_LIGHT_PROGRESS
        self.noProjectsComponent = Text(
            value=NO_PROJECTS_ADDED, color=ERROR_COLOR, visible=False
        )
        self.titleComponent = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(
                            txt=MY_PROJECTS, size=HEADLINE_4_SIZE, color=BLACK_COLOR
                        ),
                        self.progressBar,
                        self.noProjectsComponent,
                    ],
                )
            ]
        )
        self.projectsContainer = GridView(
            expand=False,
            max_extent=480,
            child_aspect_ratio=1.0,
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.projectsToDisplay = {}

    def load_all_projects(self):
        self.projectsToDisplay = self.intentHandler.get_all_projects()

    def get_all_projects_count(self):
        return self.intentHandler.get_total_projects_count()

    def display_currently_filtered_projects(self):
        self.projectsContainer.controls.clear()
        for key in self.projectsToDisplay:
            project = self.projectsToDisplay[key]
            projectCard = ProjectCard(project=project)
            self.projectsContainer.controls.append(projectCard)

    def on_filter_projects(self, filterByState: ProjectStates):
        if filterByState.value == ProjectStates.ACTIVE.value:
            self.projectsToDisplay = self.intentHandler.get_active_projects()
        elif filterByState.value == ProjectStates.UPCOMING.value:
            self.projectsToDisplay = self.intentHandler.get_upcoming_projects()
        elif filterByState.value == ProjectStates.COMPLETED.value:
            self.projectsToDisplay = self.intentHandler.get_completed_projects()
        else:
            self.projectsToDisplay = self.intentHandler.get_all_projects()
        self.display_currently_filtered_projects()
        self.update()

    def show_no_projects(self):
        self.noProjectsComponent.visible = True

    def did_mount(self):
        count = self.get_all_projects_count()
        self.progressBar.visible = False
        if count == 0:
            self.show_no_projects()
        else:
            self.load_all_projects()
            self.display_currently_filtered_projects()
        self.update()

    def build(self):
        view = Card(
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(SPACE_MD),
                content=Column(
                    controls=[
                        self.titleComponent,
                        mdSpace,
                        ProjectFiltersView(onStateChanged=self.on_filter_projects),
                        mdSpace,
                        Container(height=600, content=self.projectsContainer),
                    ]
                ),
            ),
        )
        return view
