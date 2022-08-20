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
    FilledTonalButton,
    ElevatedButton,
    IconButton,
)

import tuttle


def main(page: Page):

    application = tuttle.app.App(home_dir=".demo_home")

    rail = NavigationRail(
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
            NavigationRailDestination(
                icon=icons.WORK_OUTLINED,
                selected_icon=icons.WORK,
                label="Projects",
            ),
            NavigationRailDestination(
                icon=icons.EDIT_CALENDAR_OUTLINED,
                selected_icon=icons.EDIT_CALENDAR,
                label="Time",
            ),
            NavigationRailDestination(
                icon=icons.ATTACH_EMAIL_OUTLINED,
                selected_icon=icons.ATTACH_EMAIL,
                label="Invoicing",
            ),
            NavigationRailDestination(
                icon=icons.BUSINESS_OUTLINED,
                selected_icon=icons.BUSINESS,
                label="Banking",
            ),
            NavigationRailDestination(
                icon=icons.SETTINGS_OUTLINED,
                selected_icon_content=Icon(icons.SETTINGS),
                label_content=Text("Settings"),
            ),
        ],
        on_change=lambda e: print("Selected destination:", e.control.selected_index),
    )

    page.add(
        Row(
            [
                rail,
                VerticalDivider(width=1),
                Column(
                    [
                        Text("Body!"),
                        FilledTonalButton("Enabled button"),
                        FilledTonalButton("Disabled button", disabled=True),
                        ElevatedButton("Enabled button"),
                        ElevatedButton("Disabled button", disabled=True),
                        FloatingActionButton(icon=icons.CREATE, text="Action Button"),
                        IconButton(
                            icon=icons.CREATE,
                            tooltip="Create",
                        ),
                    ],
                    alignment="start",
                    expand=True,
                ),
            ],
            expand=True,
        )
    )


flet.app(target=main)
