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

from tuttle.controller import Controller

from views import (
    ContactView,
)


class App(UserControl):
    """Main application window."""

    def __init__(
        self,
        con: Controller,
    ):
        super().__init__()
        self.con = con

    def build(self):
        return Row(
            [
                NavigationRail(
                    destinations=[
                        NavigationRailDestination(
                            icon=icons.AREA_CHART_OUTLINED,
                            selected_icon=icons.AREA_CHART,
                            label="Dashboard",
                        )
                    ],
                    extended=True,
                ),
                VerticalDivider(width=1),
            ]
        )

    def build_(self):
        """Obligatory build method."""

        self.nav_rail = NavigationRail(
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
                self.nav_rail,
                VerticalDivider(width=1),
            ],
            expand=True,
        )


def main(page: Page):

    con = Controller(
        in_memory=True,
        verbose=True,
    )

    app = App(
        con,
    )

    # navigation = NavigationRail(
    #     selected_index=0,
    #     label_type="all",
    #     extended=True,
    #     min_width=100,
    #     min_extended_width=400,
    #     # leading=FloatingActionButton(icon=icons.CREATE, text="Add"),
    #     group_alignment=-0.9,
    #     destinations=[
    #         NavigationRailDestination(
    #             icon=icons.AREA_CHART_OUTLINED,
    #             selected_icon=icons.AREA_CHART,
    #             label="Dashboard",
    #         ),
    #     ],
    #     on_change=lambda e: print("Selected destination:", e.control.selected_index),
    # )

    page.add(
        app,
    )

    page.update()


flet.app(
    target=main,
)
