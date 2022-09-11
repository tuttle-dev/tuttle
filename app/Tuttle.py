from loguru import logger
from textwrap import dedent

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
)
from flet import icons, colors, dropdown

from layout import DesktopAppLayout

import views
import widgets

from tuttle.controller import Controller
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

    def update(self):
        super().update()

    def update_content(self):
        super().update_content()

        self.main_column.controls.clear()

        projects = self.app.con.query(Project)

        project_select = Dropdown(
            label="Project",
            hint_text="Select the project",
            options=[dropdown.Option(project.title) for project in projects],
            autofocus=True,
        )

        date_from_select = widgets.DateSelector()
        date_to_select = widgets.DateSelector()

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
                    project_select,
                ]
            ),
            Row(
                [
                    # Icon(icons.DATE_RANGE),
                    date_from_select,
                    Icon(icons.ARROW_FORWARD),
                    date_to_select,
                    TextButton(
                        "Select",
                        on_click=lambda event: logger.info(
                            f"Selected date range: {date_from_select.get_date()} -> {date_to_select.get_date()}"
                        ),
                    ),
                ]
            ),
            Row(
                [
                    ElevatedButton(
                        "Generate invoice",
                        icon=icons.EDIT_NOTE,
                        # on_click=self.add_demo_data,
                    ),
                ]
            ),
        ]
        self.update()


def main(page: Page):

    con = Controller(
        in_memory=True,
        verbose=False,
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
                label="Invocing",
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
