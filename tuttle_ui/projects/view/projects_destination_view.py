from flet import (
    Card,
    Column,
    Container,
    ElevatedButton,
    GridView,
    ResponsiveRow,
    Row,
    Text,
    border_radius,
    padding,
)

from core.ui.components.progress.horizontal_progress_bars import PRIMARY_LIGHT_PROGRESS
from core.ui.components.spacers import mdSpace
from core.ui.components.text.headlines import (
    get_headline_txt,
    get_headline_with_subtitle,
)
from core.ui.utils.flet_constants import END_ALIGNMENT, SPACE_BETWEEN_ALIGNMENT
from res.colors import BLACK_COLOR, ERROR_COLOR, PRIMARY_COLOR, WHITE_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_MD, SPACE_STD
from res.strings import MY_PROJECTS, NO_PROJECTS_ADDED, VIEW_DETAILS

from .components.projects_view_filters import ProjectFiltersView, ProjectStates
from projects.abstractions.projects_destination_view import ProjectDestinationView
from typing import Callable
import typing
from core.abstractions.local_cache import LocalCache


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

    def get_all_projects_count(self):
        """TODO returns the number of projects this user has"""
        for i in range(0, 5):
            self.projectsContainer.controls.append(
                Card(
                    elevation=2,
                    expand=True,
                    content=Container(
                        expand=True,
                        bgcolor=WHITE_COLOR,
                        padding=padding.all(SPACE_STD),
                        border_radius=border_radius.all(12),
                        content=Column(
                            controls=[
                                get_headline_with_subtitle(
                                    title=f"Project {i}",
                                    subtitle="This is a demo project",
                                ),
                                get_headline_with_subtitle(
                                    title=f"Contract #{i*2}",
                                    subtitle="Tuttle UI",
                                ),
                                get_headline_with_subtitle(
                                    title=f"Client",
                                    subtitle="Christian Tuttle",
                                ),
                                Row(
                                    alignment=SPACE_BETWEEN_ALIGNMENT,
                                    vertical_alignment=END_ALIGNMENT,
                                    expand=True,
                                    controls=[
                                        Row(
                                            controls=[
                                                Text("Status: ", color=BLACK_COLOR),
                                                Text("ACTIVE", color=PRIMARY_COLOR),
                                            ]
                                        ),
                                        ElevatedButton(text=VIEW_DETAILS),
                                    ],
                                ),
                            ],
                        ),
                    ),
                )
            )
        return 0

    def on_filter_projects(self, filterByState: ProjectStates):
        print(filterByState)

    def show_no_projects(self):
        self.noProjectsComponent.visible = True

    def did_mount(self):
        count = self.get_all_projects_count()
        self.progressBar.visible = False
        if count == 0:
            self.show_no_projects()
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
