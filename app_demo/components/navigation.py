import flet
from flet import (
    Column,
    FloatingActionButton,
    Icon,
    NavigationRail,
    NavigationRailDestination,
    Page,
    Row,
    Text,
    VerticalDivider,
    icons,
    colors,
)


def main(page: Page):

    rail = NavigationRail(
        selected_index=0,
        label_type="all",
        extended=True,
        min_width=100,
        min_extended_width=250,
        group_alignment=-0.9,
        bgcolor=colors.BLUE_GREY_900,
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
        on_change=lambda e: print("Selected destination:", e.control.selected_index),
    )

    page.add(
        Row(
            [
                rail,
                # VerticalDivider(width=1),
                Column([Text("Body!")], alignment="start", expand=True),
            ],
            expand=True,
        )
    )


flet.app(target=main)
