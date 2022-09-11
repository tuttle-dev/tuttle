import flet
from flet import (
    UserControl,
    Page,
    View,
    Text,
    Column,
    Row,
    Icon,
    Card,
    Container,
    ListTile,
    IconButton,
)
from flet import icons

from tuttle.controller import Controller
from tuttle.model import (
    Contact,
    Address,
)

from tuttle_tests.demo import demo_contact, contact_two


class App(UserControl):
    def __init__(
        self,
        con: Controller,
    ):
        super().__init__()
        self.con = con


class AppView(UserControl):
    def __init__(
        self,
        app: App,
    ):
        super().__init__()
        self.app = app


class ContactView(AppView):
    """View of the Contact model class."""

    def __init__(
        self,
        contact: Contact,
        app: App,
    ):
        super().__init__(app)
        self.contact = contact

    def get_address(self):
        if self.contact.address:
            return self.contact.address.printed
        else:
            return ""

    def delete_contact(self, event):
        """Delete the contact."""
        self.app.con.delete(self.contact)

    def build(self):
        """Obligatory build method."""
        self.view = Card(
            content=Container(
                content=Column(
                    [
                        ListTile(
                            leading=Icon(icons.CONTACT_MAIL),
                            title=Text(self.contact.name),
                            subtitle=Column(
                                [
                                    Text(self.contact.email),
                                    Text(self.get_address()),
                                ]
                            ),
                        ),
                        Row(
                            [
                                IconButton(
                                    icon=icons.EDIT,
                                ),
                                IconButton(
                                    icon=icons.DELETE,
                                    on_click=self.delete_contact,
                                ),
                            ],
                            alignment="end",
                        ),
                    ]
                ),
                # width=400,
                padding=10,
            )
        )
        return self.view


def main(page: Page):

    con = Controller(
        in_memory=True,
        verbose=True,
    )

    con.store(demo_contact)
    con.store(contact_two)

    app = App(
        con,
    )

    for contact in con.contacts:
        page.add(ContactView(contact, app))

    page.update()


flet.app(
    target=main,
)
