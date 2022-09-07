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
    CircleAvatar,
)
from flet import icons, colors

from tuttle.model import (
    User,
    Address,
    BankAccount,
)


def demo_user():
    user = User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        website="https://tuttle-dev.github.io/tuttle/",
        email="mail@tuttle.com",
        phone_number="+55555555555",
        VAT_number="27B-6",
        address=Address(
            name="Harry Tuttle",
            street="Main Street",
            number="450",
            city="Sao Paolo",
            postal_code="555555",
            country="Brazil",
        ),
        bank_account=BankAccount(
            name="Giro",
            IBAN="BZ99830994950003161565",
        ),
    )
    return user


class UserView(UserControl):
    """Main class of the application GUI."""

    def __init__(
        self,
        user: User,
    ):
        super().__init__()
        self.user = user

    def build(self):
        """Obligatory build method."""

        self.avatar = CircleAvatar(
            content=Icon(icons.PERSON),
            bgcolor=colors.WHITE,
        )

        self.view = Column(
            [
                Row(
                    [
                        self.avatar,
                        Text(
                            self.user.name,
                            weight="bold",
                        ),
                    ]
                ),
                Row(
                    [
                        Text(
                            self.user.email,
                            italic=True,
                        ),
                    ]
                ),
            ]
        )

        return self.view


def main(page: Page):

    user_view = UserView(
        user=demo_user(),
    )

    page.add(
        user_view,
    )

    page.update()


flet.app(
    target=main,
)
