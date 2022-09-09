from copy import deepcopy

import flet
from flet import (
    AppBar,
    Column,
    Row,
    Container,
    IconButton,
    Icon,
    NavigationRail,
    NavigationRailDestination,
    Page,
    Text,
    Card,
)
from flet import colors, icons


class NavigationItem:
    """An item in the NavigationRail."""

    def __init__(
        self,
        name,
        icon: Icon,
        selected_icon: Icon = None,
    ):
        self.name = name
        self.icon = icon
        self.selected_icon = selected_icon


class MenuLayout(Row):
    """A desktop app layout with a menu on the left."""

    def __init__(
        self,
        page,
        pages,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.page = page
        self.pages = pages

        self.expand = True

        self.navigation_items = [navigation_item for navigation_item, _ in pages]
        self.navigation_rail = self.build_navigation_rail()
        self.update_destinations()
        self._menu_extended = True
        self.navigation_rail.extended = True

        page_contents = [page_content for _, page_content in pages]

        self.menu_panel = Row(
            controls=[
                self.navigation_rail,
            ],
            spacing=0,
            tight=True,
        )
        self.content_area = Column(page_contents, expand=True)

        self._was_portrait = self.is_portrait()
        self._panel_visible = self.is_landscape()

        self.set_navigation_content()

        self._change_displayed_page()

        self.page.on_resize = self.handle_resize

    def select_page(self, page_number):
        self.navigation_rail.selected_index = page_number
        self._change_displayed_page()

    def _navigation_change(self, e):
        self._change_displayed_page()
        self.page.update()

    def _change_displayed_page(self):
        page_number = self.navigation_rail.selected_index
        for i, content_page in enumerate(self.content_area.controls):
            content_page.visible = page_number == i

    def build_navigation_rail(self):
        return NavigationRail(
            selected_index=0,
            label_type="none",
            on_change=self._navigation_change,
            # bgcolor=colors.SURFACE_VARIANT,
        )

    def update_destinations(self):
        navigation_items = self.navigation_items

        self.navigation_rail.destinations = [
            NavigationRailDestination(**nav_specs) for nav_specs in navigation_items
        ]
        self.navigation_rail.label_type = "all"

    def handle_resize(self, e):
        pass

    def set_navigation_content(self):
        self.controls = [self.menu_panel, self.content_area]
        self.update_destinations()
        self.navigation_rail.extended = self._menu_extended
        self.menu_panel.visible = self._panel_visible

    def is_portrait(self) -> bool:
        # Return true if window/display is narrow
        # return self.page.window_height >= self.page.window_width
        return self.page.height >= self.page.width

    def is_landscape(self) -> bool:
        # Return true if window/display is wide
        return self.page.width > self.page.height


def create_page(title: str, body: str):
    return Row(
        controls=[
            Column(
                horizontal_alignment="stretch",
                controls=[
                    Card(content=Container(Text(title, weight="bold"), padding=8)),
                    Text(body),
                ],
                expand=True,
            ),
        ],
        expand=True,
    )


def main(page: Page, title="Basic Responsive Menu"):

    page.title = title
    page.window_width, page.window_height = (1280, 720)

    page.appbar = AppBar(
        # leading=menu_button,
        # leading_width=40,
        # bgcolor=colors.SURFACE_VARIANT,
    )

    pages = [
        (
            dict(
                icon=icons.LANDSCAPE_OUTLINED,
                selected_icon=icons.LANDSCAPE,
                label="Menu in landscape",
            ),
            create_page(
                "Menu in landscape",
                "Menu in landscape is by default shown, side by side with the main content, but can be "
                "hidden with the menu button.",
            ),
        ),
        (
            dict(
                icon=icons.PORTRAIT_OUTLINED,
                selected_icon=icons.PORTRAIT,
                label="Menu in portrait",
            ),
            create_page(
                "Menu in portrait",
                "Menu in portrait is mainly expected to be used on a smaller mobile device."
                "\n\n"
                "The menu is by default hidden, and when shown with the menu button it is placed on top of the main "
                "content."
                "\n\n"
                "In addition to the menu button, menu can be dismissed by a tap/click on the main content area.",
            ),
        ),
        (
            dict(
                icon=icons.INSERT_EMOTICON_OUTLINED,
                selected_icon=icons.INSERT_EMOTICON,
                label="Minimize to icons",
            ),
            create_page(
                "Minimize to icons",
                "ResponsiveMenuLayout has a parameter minimize_to_icons. "
                "Set it to True and the menu is shown as icons only, when normally it would be hidden.\n"
                "\n\n"
                "Try this with the 'Minimize to icons' toggle in the top bar."
                "\n\n"
                "There are also landscape_minimize_to_icons and portrait_minimize_to_icons properties that you can "
                "use to set this property differently in each orientation.",
            ),
        ),
        (
            dict(
                icon=icons.COMPARE_ARROWS_OUTLINED,
                selected_icon=icons.COMPARE_ARROWS,
                label="Menu width",
            ),
            create_page(
                "Menu width",
                "ResponsiveMenuLayout has a parameter manu_extended. "
                "Set it to False to place menu labels under the icons instead of beside them."
                "\n\n"
                "Try this with the 'Menu width' toggle in the top bar.",
            ),
        ),
        (
            dict(
                icon=icons.PLUS_ONE_OUTLINED,
                selected_icon=icons.PLUS_ONE,
                label="Fine control",
            ),
            create_page(
                "Adjust navigation rail",
                "NavigationRail is accessible via the navigation_rail attribute of the ResponsiveMenuLayout. "
                "In this demo it is used to add the leading button control."
                "\n\n"
                "These NavigationRail attributes are used by the ResponsiveMenuLayout, and changing them directly "
                "will probably break it:\n"
                "- destinations\n"
                "- extended\n"
                "- label_type\n"
                "- on_change\n",
            ),
        ),
    ]

    menu_layout = MenuLayout(page, pages)

    page.add(menu_layout)

    page.appbar.actions = [
        Row(
            [
                IconButton(
                    icon=icons.HELP,
                )
            ]
        )
    ]


if __name__ == "__main__":
    flet.app(
        target=main,
    )
