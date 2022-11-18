from flet import Card, Column, Container, ResponsiveRow, Text, UserControl, padding
from core.ui.components.spacers import mdSpace
from core.ui.components.progress.horizontal_progress_bars import PRIMARY_LIGHT_PROGRESS
from core.ui.components.text.headlines import get_headline_txt
from res.colors import (
    BLACK_COLOR,
    ERROR_COLOR,
)
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_MD
from res.strings import MY_PROJECTS, NO_PROJECTS_ADDED
from .components.projects_view_filters import ProjectFiltersView, ProjectStates


class ProjectsDestinationView(UserControl):
    def __init__(self):
        super().__init__()
        self.progressBar = PRIMARY_LIGHT_PROGRESS
        self.titleComponent = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(
                            txt=MY_PROJECTS, size=HEADLINE_4_SIZE, color=BLACK_COLOR
                        ),
                        self.progressBar,
                    ],
                )
            ]
        )
        self.noProjectsComponent = Text(value=NO_PROJECTS_ADDED, color=ERROR_COLOR)

    def get_all_projects_count(self):
        """TODO returns the number of projects this user has"""
        return 0

    def on_filter_projects(self, filterByState: ProjectStates):
        print(filterByState)

    def show_no_projects(self):
        self.titleComponent.controls.append(self.noProjectsComponent)

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
                    ]
                ),
            ),
        )
        return view
