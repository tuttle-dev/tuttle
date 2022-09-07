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
from flet import icons


class App(UserControl):
    """Main class of the application GUI."""

    def __init__(
        self,
    ):
        super().__init__()

    def build(self):
        """Obligatory build method."""

        self.navigation = NavigationRail(
            selected_index=0,
            label_type="all",
            extended=True,
            min_width=100,
            min_extended_width=400,
            # leading=FloatingActionButton(icon=icons.CREATE, text="Add"),
            group_alignment=-0.9,
            destinations=[
                NavigationRailDestination(
                    icon=icons.AREA_CHART_OUTLINED,
                    selected_icon=icons.AREA_CHART,
                    label="Dashboard",
                ),
            ],
            on_change=lambda e: print(
                "Selected destination:", e.control.selected_index
            ),
        )

        return Row(
            [
                self.navigation,
                VerticalDivider(width=1),
            ],
            expand=True,
        )


def main(page: Page):

    navigation = NavigationRail(
        selected_index=0,
        label_type="all",
        extended=True,
        min_width=100,
        min_extended_width=400,
        # leading=FloatingActionButton(icon=icons.CREATE, text="Add"),
        group_alignment=-0.9,
        destinations=[
            NavigationRailDestination(
                icon=icons.AREA_CHART_OUTLINED,
                selected_icon=icons.AREA_CHART,
                label="Dashboard",
            ),
        ],
        on_change=lambda e: print("Selected destination:", e.control.selected_index),
    )

    page.add(
        Row(
            [
                navigation,
                VerticalDivider(width=0),
            ],
            expand=True,
        )
    )

    page.update()


flet.app(
    target=main,
)
