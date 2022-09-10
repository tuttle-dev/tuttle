from loguru import logger

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
)
from flet import icons, colors

from layout import DesktopAppLayout

import views
from views import (
    ContactView,
    ContactView2,
)

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
            [
                # Contacts listed here
            ],
        )
        self.view = Row([self.main_column])

        return self.view

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
        self.view.controls[0].controls.clear()
        self.view.controls[0].controls.append(
            Text("Demo data installed ☑️"),
        )
        self.update()

    def build(self):
        self.view = Row(
            [
                Column(
                    [
                        ElevatedButton(
                            "Install demo data",
                            icon=icons.TOYS,
                            on_click=self.add_demo_data,
                        ),
                    ],
                )
            ]
        )
        return self.view


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
                label="Invoices",
            ),
            AppPage(app),
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
