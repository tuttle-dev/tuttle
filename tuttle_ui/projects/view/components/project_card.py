from flet import (
    UserControl,
    Card,
    Column,
    Container,
    ElevatedButton,
    Row,
    Text,
    border_radius,
    padding,
)
from res.strings import (
    START_DATE,
    END_DATE,
    CLIENT_ID_LBL,
    CONTRACT_ID_LBL,
    PROJECT_TAG,
)
from core.ui.components.text.headlines import (
    get_headline_with_subtitle,
)
from core.ui.utils.flet_constants import END_ALIGNMENT, SPACE_BETWEEN_ALIGNMENT
from res.colors import BLACK_COLOR, WHITE_COLOR, PRIMARY_COLOR, ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_STD
from res.strings import VIEW_DETAILS

from typing import Callable
import typing
from projects.model.projects_model import Project


class ProjectCard(UserControl):
    """Formats a single project info into a card ui display"""

    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.productInfoContainer = Column()

    def build(self):
        self.productInfoContainer.controls = [
            get_headline_with_subtitle(
                title=self.project.title,
                subtitle=self.project.description,
                titleSize=HEADLINE_4_SIZE,
            ),
            Text(
                f"{CONTRACT_ID_LBL}{self.project.contract_id}",
            ),
            Text(f"{CLIENT_ID_LBL}{self.project.client_id}"),
            Text(f"{START_DATE} {self.project.get_start_date_as_str()}"),
            Text(f"{END_DATE} {self.project.get_end_date_as_str()}", color=ERROR_COLOR),
            Row(
                alignment=SPACE_BETWEEN_ALIGNMENT,
                vertical_alignment=END_ALIGNMENT,
                expand=True,
                controls=[
                    Row(
                        spacing=0,
                        controls=[
                            Text(f"{PROJECT_TAG}", color=BLACK_COLOR),
                            Text(f"{self.project.unique_tag}", color=PRIMARY_COLOR),
                        ],
                    ),
                    ElevatedButton(text=VIEW_DETAILS),
                ],
            ),
        ]
        card = Card(
            elevation=2,
            expand=True,
            content=Container(
                expand=True,
                bgcolor=WHITE_COLOR,
                padding=padding.all(SPACE_STD),
                border_radius=border_radius.all(12),
                content=self.productInfoContainer,
            ),
        )
        return card
