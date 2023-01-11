from typing import Callable

from flet import (
    AlertDialog,
    Card,
    Column,
    Container,
    GridView,
    IconButton,
    ListTile,
    ResponsiveRow,
    Row,
    Text,
    UserControl,
    border_radius,
    icons,
    Icon,
    padding,
)

from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from core.models import IntentResult
from core.utils import AlertDialogControls, START_ALIGNMENT

from core.views import (
    CENTER_ALIGNMENT,
    StandardDropdown,
    get_dropdown,
    get_headline_txt,
    get_primary_btn,
    get_std_txt_field,
    horizontal_progress,
    mdSpace,
    xsSpace,
)
from loguru import logger
from projects.intent import ProjectsIntent
from res import colors, fonts
from res.colors import ERROR_COLOR, GRAY_COLOR
from res.dimens import (
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SPACE_MD,
    SPACE_STD,
    SPACE_XS,
)
from res.fonts import (
    BODY_1_SIZE,
    BODY_2_SIZE,
    HEADLINE_4_SIZE,
    SUBTITLE_1_SIZE,
    SUBTITLE_2_SIZE,
)


from tuttle.model import Invoice

from .intent import InvoicingIntent


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


class InvoiceCard(UserControl):
    """Formats a single invoice info into a card ui display"""

    def __init__(self, invoice: Invoice, on_edit_clicked: Callable[[str], None]):
        super().__init__()
        self.invoice = invoice
        self.invoice_info_container = Column(
            spacing=0,
            run_spacing=0,
        )
        self.on_edit_clicked = on_edit_clicked

    def build(self):
        self.invoice_info_container.controls = [
            ListTile(
                leading=Icon(icons.INVOICE),
                title=Text(self.invoice.number),
                subtitle=Text(f"Date: {self.invoice.date}", color=GRAY_COLOR),
                trailing=IconButton(
                    icon=icons.EDIT_NOTE_OUTLINED,
                    tooltip="Edit Invoice",
                    on_click=lambda e: self.on_edit_clicked(self.invoice),
                ),
            ),
            mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "Client",
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Text(
                        self.invoice.client.name,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                ],
                spacing=SPACE_XS,
                run_spacing=0,
                vertical_alignment=CENTER_ALIGNMENT,
            ),
            mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "Amount",
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        Text(
                            self.invoice.total,
                            size=BODY_2_SIZE,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=START_ALIGNMENT,
                vertical_alignment=START_ALIGNMENT,
                spacing=SPACE_XS,
                run_spacing=0,
            ),
            mdSpace,
            ResponsiveRow(
                controls=[
                    Text(
                        "Status",
                        color=GRAY_COLOR,
                        size=BODY_2_SIZE,
                        col={"xs": "12"},
                    ),
                    Container(
                        Text(
                            self.invoice.status,
                            size=BODY_2_SIZE,
                            col={"xs": "12"},
                        ),
                    ),
                ],
                alignment=START_ALIGNMENT,
                vertical_alignment=START_ALIGNMENT,
                spacing=SPACE_XS,
                run_spacing=0,
            ),
        ]
        card = Card(
            elevation=2,
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(SPACE_STD),
                border_radius=border_radius.all(12),
                content=self.invoice_info_container,
            ),
        )
        return card


class InvoiceTile(UserControl):
    """
    A UserControl that formats an invoice object as a list tile for display in the UI
    """

    def __init__(self, invoice: Invoice):
        super().__init__()
        self.invoice = invoice

    def build(self):
        """
        Build and return a ListTile displaying the invoice information
        """
        return ListTile(
            leading=Text(self.invoice.number),
            title=Text(self.invoice.client.name),
            subtitle=Text(self.invoice.date.strftime("%d-%m-%Y")),
            trailing=Text(str(self.invoice.total)),
        )
