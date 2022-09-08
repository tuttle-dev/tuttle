import flet
from flet import (
    UserControl,
    Page,
    View,
    Text,
    Column,
    Row,
    KeyboardEvent,
    SnackBar,
    NavigationRail,
    NavigationRailDestination,
    VerticalDivider,
    Icon,
)
from flet import icons, colors

from tuttle.controller import Controller
from tuttle.model import (
    Contact,
)

from views import (
    ContactView,
)


class ContactsView(UserControl):
    def __init__(
        self,
        app: "App",
    ):
        super().__init__()
        self.app = app

    def build(self):

        contacts = self.app.con.query(Contact)

        return Text(f"contacts: {' '.join(contacts)}")


class App(UserControl):
    """Main application window."""

    def __init__(
        self,
        con: Controller,
        page: Page,
    ):
        super().__init__()
        self.con = con
        self.page = page

    def build(self):

        self.contacts_view = ContactsView(self)

        self.main_view = Column(
            [
                Text("Main application window"),
            ],
            alignment="start",
            expand=True,
        )
        return self.main_view

    def attach_navigation(self, nav: NavigationRail):
        # FIXME: workaround
        self.nav = nav

    def on_navigation_change(self, event):
        print(event.control.selected_index)
        self.main_view.controls.clear()
        if event.control.selected_index == 3:
            self.main_view.controls.append(self.contacts_view)
        else:
            self.main_view.controls.append(
                Text(f"selected destination {event.control.selected_index}")
            )
        self.update()

    def update(self):
        super().update()


def main(page: Page):

    con = Controller(
        in_memory=True,
        verbose=False,
    )

    app = App(
        con,
        page,
    )

    nav = NavigationRail(
        selected_index=0,
        label_type="all",
        extended=True,
        min_width=100,
        min_extended_width=250,
        group_alignment=-0.9,
        # bgcolor=colors.BLUE_GREY_900,
        destinations=[
            NavigationRailDestination(
                icon=icons.SPEED,
                label="Dashboard",
            ),
            NavigationRailDestination(
                icon=icons.WORK,
                label="Projects",
            ),
            NavigationRailDestination(
                icon=icons.DATE_RANGE,
                label="Time Tracking",
            ),
            NavigationRailDestination(
                icon=icons.CONTACT_MAIL,
                label="Contacts",
            ),
            NavigationRailDestination(
                icon=icons.HANDSHAKE,
                label="Clients",
            ),
            NavigationRailDestination(
                icon=icons.HISTORY_EDU,
                label="Contracts",
            ),
            NavigationRailDestination(
                icon=icons.OUTGOING_MAIL,
                label="Invoices",
            ),
            NavigationRailDestination(
                icon=icons.SETTINGS,
                label_content=Text("Settings"),
            ),
        ],
        on_change=app.on_navigation_change,
    )

    app.attach_navigation(nav)

    page.add(
        Row(
            [
                nav,
                # VerticalDivider(width=1),
                app,
            ],
            expand=True,
        )
    )

    page.update()


flet.app(
    target=main,
)
