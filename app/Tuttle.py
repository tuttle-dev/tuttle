import datetime
from loguru import logger
from textwrap import dedent
from pathlib import Path

import flet
from flet import (
    Page,
    Row,
    Column,
    Container,
    Text,
    Card,
    NavigationRailDestination,
    UserControl,
    ElevatedButton,
    TextButton,
    Icon,
    Dropdown,
    Markdown,
    FilePicker,
    FilePickerResultEvent,
)
from flet import icons, colors, dropdown

from layout import DesktopAppLayout

import views
import widgets

from tuttle.controller import Controller
from tuttle.preferences import Preferences
from tuttle.model import (
    Contact,
    Contract,
    Project,
    Client,
)

from tuttle_tests import demo


class App:
    def __init__(
        self,
        controller: Controller,
        page: Page,
    ):
        self.con = controller
        self.page = page


class AppPage(UserControl):
    def __init__(
        self,
        app: App,
    ):
        super().__init__()
        self.app = app

    def build(self):
        self.main_column = Column(
            scroll="auto",
        )
        # self.view = Row([self.main_column])

        return self.main_column

    def update_content(self):
        pass


class DemoPage(AppPage):
    def __init__(
        self,
        app: App,
    ):
        super().__init__(app)

    def update(self):
        super().update()

    def add_demo_data(self, event):
        """Install the demo data on button click."""
        demo.add_demo_data(self.app.con)
        self.main_column.controls.clear()
        self.main_column.controls.append(
            Text("Demo data installed ☑️"),
        )
        self.update()

    def build(self):
        self.main_column = Column(
            [
                ElevatedButton(
                    "Install demo data",
                    icon=icons.TOYS,
                    on_click=self.add_demo_data,
                ),
            ],
        )
        return self.main_column


class ContactsPage(AppPage):
    def __init__(
        self,
        app: App,
    ):
        super().__init__(app)

    def update(self):
        super().update()

    def update_content(self):
        super().update_content()
        self.main_column.controls.clear()

        contacts = self.app.con.query(Contact)

        for contact in contacts:
            self.main_column.controls.append(
                views.make_contact_view(contact),
            )
        self.update()


class ContractsPage(AppPage):
    def __init__(
        self,
        app: App,
    ):
        super().__init__(app)

    def update(self):
        super().update()

    def update_content(self):
        super().update_content()
        self.main_column.controls.clear()

        contracts = self.app.con.query(Contract)

        for contract in contracts:
            self.main_column.controls.append(
                # TODO: replace with view class
                views.make_contract_view(contract)
            )
        self.update()


class ProjectsPage(AppPage):
    def __init__(
        self,
        app: App,
    ):
        super().__init__(app)

    def update(self):
        super().update()

    def update_content(self):
        super().update_content()
        self.main_column.controls.clear()

        projects = self.app.con.query(Project)

        for project in projects:
            self.main_column.controls.append(
                # TODO: replace with view class
                views.make_project_view(project)
            )
        self.update()


class InvoicingPage(AppPage):
    """A page for the invoicing workflow."""

    def __init__(
        self,
        app: App,
    ):
        super().__init__(app)
        self.calendar_file_path = None

    def update(self):
        super().update()

    def on_click_generate_invoices(self, event):
        """Generate invoices for the selected project and date range."""
        logger.info("Generate invoices clicked")
        if not self.calendar_file_path:
            logger.error("No calendar file selected!")
            return
        self.app.con.billing(
            project_tags=[self.project_select.value],
            period_start=str(self.date_from_select.get_date()),
            period_end=str(self.date_to_select.get_date()),
            timetracking_method="file_calendar",
            calendar_file_path=self.calendar_file_path,
        )

    def on_pick_calendar_file(self, event: FilePickerResultEvent):
        """Handle the result of the calendar file picker."""
        if event.files:
            logger.info(f"Calendar file picked: {event.files[0].path}")
            self.calendar_file_path = Path(event.files[0].path)
        else:
            logger.info("Cancelled!")

    def update_content(self):
        super().update_content()

        self.main_column.controls.clear()

        self.calendar_file_picker = FilePicker(on_result=self.on_pick_calendar_file)

        self.app.page.overlay.append(self.calendar_file_picker)

        # select project
        projects = self.app.con.query(Project)

        self.project_select = Dropdown(
            label="Project",
            hint_text="Select the project",
            options=[dropdown.Option(project.tag) for project in projects],
            autofocus=True,
        )

        self.date_from_select = widgets.DateSelector(preset=datetime.date(2022, 1, 1))
        self.date_to_select = widgets.DateSelector(preset=datetime.date(2022, 12, 31))

        self.main_column.controls = [
            Row(
                [
                    Text("Invoicing Workflow Demo", style="headlineMedium"),
                ]
            ),
            Row(
                [
                    views.make_card(
                        [
                            Text(
                                dedent(
                                    """
                            1. select a time tracking data source
                            """
                                )
                            )
                        ]
                    )
                ]
            ),
            Row(
                [
                    ElevatedButton(
                        "Pick Calendar File",
                        icon=icons.UPLOAD_FILE,
                        on_click=lambda _: self.calendar_file_picker.pick_files(
                            allow_multiple=False
                        ),
                    ),
                ]
            ),
            Row(
                [
                    views.make_card(
                        [
                            Text(
                                dedent(
                                    """
                            2. select a project and date range
                            """
                                )
                            )
                        ]
                    )
                ]
            ),
            Row(
                [
                    Icon(icons.WORK),
                    self.project_select,
                ]
            ),
            Row(
                [
                    # Icon(icons.DATE_RANGE),
                    self.date_from_select,
                    Icon(icons.ARROW_FORWARD),
                    self.date_to_select,
                    TextButton(
                        "Select",
                        on_click=lambda event: logger.info(
                            f"Selected date range: {self.date_from_select.get_date()} -> {self.date_to_select.get_date()}"
                        ),
                    ),
                ]
            ),
            Row(
                [
                    ElevatedButton(
                        "Generate invoice",
                        icon=icons.EDIT_NOTE,
                        on_click=self.on_click_generate_invoices,
                    ),
                ]
            ),
        ]
        self.update()


def main(page: Page):

    con = Controller(
        in_memory=True,
        verbose=False,
        preferences=Preferences(
            invoice_dir=Path("Invoices"),
        ),
    )

    app = App(
        controller=con,
        page=page,
    )

    pages = [
        (
            NavigationRailDestination(
                icon=icons.TOYS_OUTLINED,
                selected_icon=icons.TOYS,
                label="Demo",
            ),
            DemoPage(app),
        ),
        (
            NavigationRailDestination(
                icon=icons.SPEED_OUTLINED,
                selected_icon=icons.SPEED,
                label="Dashboard",
            ),
            AppPage(app),
        ),
        (
            NavigationRailDestination(
                icon=icons.WORK,
                label="Projects",
            ),
            ProjectsPage(app),
        ),
        (
            NavigationRailDestination(
                icon=icons.DATE_RANGE,
                label="Time",
            ),
            AppPage(app),
        ),
        (
            NavigationRailDestination(
                icon=icons.CONTACT_MAIL,
                label="Contacts",
            ),
            ContactsPage(app),
        ),
        (
            NavigationRailDestination(
                icon=icons.HANDSHAKE,
                label="Clients",
            ),
            AppPage(app),
        ),
        (
            NavigationRailDestination(
                icon=icons.HISTORY_EDU,
                label="Contracts",
            ),
            ContractsPage(app),
        ),
        (
            NavigationRailDestination(
                icon=icons.OUTGOING_MAIL,
                label="Invoicing",
            ),
            InvoicingPage(app),
        ),
        (
            NavigationRailDestination(
                icon=icons.SETTINGS,
                label_content=Text("Settings"),
            ),
            AppPage(app),
        ),
    ]

    layout = DesktopAppLayout(
        page=page,
        pages=pages,
        title="Tuttle",
        window_size=(1280, 720),
    )

    page.add(
        layout,
    )


if __name__ == "__main__":
    flet.app(
        target=main,
    )
