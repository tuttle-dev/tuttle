from loguru import logger

from flet import Column, Container, ResponsiveRow, UserControl

from core.views import (
    mdSpace,
    StandardDropdown,
    get_headline_txt,
    get_dropdown,
)
from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from core.models import IntentResult
from core.utils import AlertDialogControls
from res import colors, fonts

from .intent import InvoicingIntent

from projects.intent import ProjectsIntent


class InvoicingView(TuttleView, UserControl):
    def __init__(
        self,
        params: TuttleViewParams,
    ):
        super().__init__(params)
        self.intent_handler = InvoicingIntent()
        self.projects_intent_handler = ProjectsIntent()

        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt="Invoicing", size=fonts.HEADLINE_4_SIZE),
                    ],
                )
            ]
        )

    def on_project_change(self, value):
        raise NotImplementedError("ToDO")

    def build(self):

        project_options = [
            project.title
            for id, project in self.projects_intent_handler.get_all_projects_as_map().items()
        ]
        logger.info(f"project_options: {project_options}")

        # self.project_selector = StandardDropdown(
        #     label="Project",
        #     options=project_options,
        #     initial_value="Select a project",
        #     on_change=self.on_project_change,
        # )
        self.project_selector = get_dropdown(
            label="Project",
            items=project_options,
            initial_value="Select a project",
            on_change=self.on_project_change,
        )
        # FIXME: dropdown options are not shown

        view = Column(
            controls=[
                self.title_control,
                mdSpace,
                self.project_selector,
            ]
        )
        return view
