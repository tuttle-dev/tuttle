from flet import (
    UserControl,
    Card,
    Column,
    Container,
    ElevatedButton,
    Row,
    Text,
    ResponsiveRow,
    border_radius,
    padding,
)
from res.strings import (
    START_DATE,
    END_DATE,
    CLIENT_LBL,
    CONTRACT_LBL,
    HASH_TAG,
)
from core.views import (
    get_headline_with_subtitle,
)
from core.constants_and_enums import (
    END_ALIGNMENT,
    SPACE_BETWEEN_ALIGNMENT,
    CENTER_ALIGNMENT,
)
from res.colors import ERROR_COLOR, GRAY_COLOR, PRIMARY_COLOR
from res.fonts import HEADLINE_4_SIZE, BODY_2_SIZE
from res.dimens import SPACE_STD, SPACE_XS
from res.strings import VIEW_DETAILS

from typing import Callable
from projects.project_model import Project


class ProjectCard(UserControl):
    """Formats a single project info into a card ui display"""

    def __init__(self, project: Project, onClickView: Callable[[str], None]):
        super().__init__()
        self.project = project
        self.productInfoContainer = Column()
        self.onClickView = onClickView

    def build(self):
        self.productInfoContainer.controls = [
            get_headline_with_subtitle(
                title=self.project.title,
                subtitle=self.project.get_brief_description(),
                titleSize=HEADLINE_4_SIZE,
                subtitleColor=GRAY_COLOR,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        CONTRACT_LBL,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.project.contract.title,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        CLIENT_LBL,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.project.contract.client.title,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        START_DATE,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.project.get_start_date_as_str(),
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            ResponsiveRow(
                controls=[
                    Text(
                        END_DATE,
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12", "sm": "5", "md": "3"},
                    ),
                    Text(
                        self.project.get_end_date_as_str(),
                        size=BODY_2_SIZE,
                        color=ERROR_COLOR,
                        col={"xs": "12", "sm": "7", "md": "9"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            Row(
                alignment=SPACE_BETWEEN_ALIGNMENT,
                vertical_alignment=END_ALIGNMENT,
                expand=True,
                controls=[
                    Row(
                        spacing=0,
                        controls=[
                            Text(f"{HASH_TAG}", color=PRIMARY_COLOR),
                            Text(f"{self.project.unique_tag}", color=GRAY_COLOR),
                        ],
                    ),
                    ElevatedButton(
                        text=VIEW_DETAILS,
                        on_click=lambda e: self.onClickView(self.project.id),
                    ),
                ],
            ),
        ]
        card = Card(
            elevation=2,
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(SPACE_STD),
                border_radius=border_radius.all(12),
                content=self.productInfoContainer,
            ),
        )
        return card
