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

from tuttle.model import (
    Contact,
    Address,
)


class ContactView(UserControl):
    """Main class of the application GUI."""

    def __init__(
        self,
        contact: Contact,
    ):
        super().__init__()
        self.contact = contact

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
                                    Text(self.contact.address.printed),
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

    demo_contact = Contact(
        name="Sam Lowry",
        email="info@centralservices.com",
        address=Address(
            street="Main Street",
            number="9999",
            postal_code="55555",
            city="Sao Paolo",
            country="Brazil",
        ),
    )

    page.add(
        ContactView(demo_contact),
        ContactView(demo_contact),
    )

    page.update()


flet.app(
    target=main,
)
