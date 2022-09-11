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
    Card,
    Container,
    ListTile,
    TextButton,
)
from flet import icons

from tuttle.model import Contract


class ContractView(UserControl):
    """Main class of the application GUI."""

    def __init__(
        self,
        contract: Contract,
    ):
        super().__init__()
        self.contract = contract

    def build(self):
        """Obligatory build method."""
        self.view = Card(
            content=Container(
                content=Column(
                    [
                        ListTile(
                            leading=Icon(icons.HISTORY_EDU),
                            title=Text(self.contract.title),
                            subtitle=Text(self.contract.client.name),
                        ),
                        Row(
                            [TextButton("Buy tickets"), TextButton("Listen")],
                            alignment="end",
                        ),
                    ]
                ),
                width=400,
                padding=10,
            )
        )
