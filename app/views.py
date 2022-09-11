from typing import Optional, List, Tuple
import datetime

from flet import (
    UserControl,
    Card,
    Container,
    Column,
    Row,
    ListTile,
    Icon,
    IconButton,
    Text,
    PopupMenuButton,
    PopupMenuItem,
)
from flet import icons

from tuttle.model import (
    Contact,
    Contract,
    Project,
)


class AppView(UserControl):
    def __init__(
        self,
        app,
    ):
        super().__init__()
        self.app = app


class ContactView(AppView):
    """View of the Contact model class."""

    def __init__(
        self,
        contact: Contact,
        app,
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


class ContactView2(Card):
    def __init__(
        self,
        contact: Contact,
        app,
    ):
        super().__init__()
        self.contact = contact
        self.app = app

        self.content = Container(
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
                                # on_click=self.delete_contact,
                            ),
                        ],
                        alignment="end",
                    ),
                ]
            ),
            # width=400,
            padding=10,
        )

        # self.app.page.add(self)

    def get_address(self):
        if self.contact.address:
            return self.contact.address.printed
        else:
            return ""


def make_contact_view(contact: Contact):
    return Card(
        content=Container(
            content=Column(
                [
                    ListTile(
                        leading=Icon(icons.CONTACT_MAIL),
                        title=Text(contact.name),
                        subtitle=Column(
                            [
                                Text(contact.email),
                                Text(contact.print_address()),
                            ]
                        ),
                    ),
                    # Row(
                    #     [
                    #         IconButton(
                    #             icon=icons.EDIT,
                    #         ),
                    #         IconButton(
                    #             icon=icons.DELETE,
                    #         ),
                    #     ],
                    #     alignment="end",
                    # ),
                ]
            ),
            # width=400,
            padding=10,
        )
    )


def make_contract_view(contract: Contract):
    return Card(
        content=Container(
            content=Row(
                [
                    Icon(icons.HISTORY_EDU),
                    Text(contract.title),
                ],
            ),
            padding=12,
        )
    )


def make_project_view(project: Project):
    return Card(
        content=Container(
            content=Column(
                [
                    ListTile(
                        leading=Icon(icons.WORK),
                        title=Text(project.title),
                        subtitle=Text(project.tag),
                        trailing=PopupMenuButton(
                            icon=icons.MORE_VERT,
                            items=[
                                PopupMenuItem(
                                    icon=icons.EDIT,
                                    text="Edit",
                                ),
                                PopupMenuItem(
                                    icon=icons.DELETE,
                                    text="Delete",
                                ),
                            ],
                        ),
                    ),
                    Column(
                        [
                            Text(f"Client: {project.client.name}"),
                            Text(f"Contract: {project.contract.title}"),
                            Text(f"Start: {project.start_date}"),
                            Text(f"End: {project.end_date}"),
                        ]
                    ),
                ]
            ),
            # width=400,
            padding=10,
        )
    )


def make_card(content):
    """Make a card with the given content."""
    return Card(
        Container(
            Row(content),
            padding=10,
            expand=True,
        )
    )
