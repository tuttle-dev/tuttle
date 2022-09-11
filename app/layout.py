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
    Divider,
)
from flet import colors, icons


class DesktopAppLayout(Row):
    """A desktop app layout with a menu on the left."""

    def __init__(
        self,
        title,
        page,
        pages,
        *args,
        window_size=(800, 600),
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

        self.menu_panel = Row(
            controls=[
                self.navigation_rail,
            ],
            spacing=0,
            tight=True,
        )

        page_contents = [page_content for _, page_content in pages]
        self.content_area = Column(page_contents, expand=True)

        self._was_portrait = self.is_portrait()
        self._panel_visible = self.is_landscape()

        self.set_content()

        self._change_displayed_page()

        self.page.on_resize = self.handle_resize

        self.page.appbar = self.create_appbar()

        self.window_size = window_size
        self.page.window_width, self.page.window_height = self.window_size

        self.page.title = title

    def select_page(self, page_number):
        self.navigation_rail.selected_index = page_number
        self._change_displayed_page()

    def _navigation_change(self, e):
        self._change_displayed_page()
        self.page.update()

    def _change_displayed_page(self):
        page_number = self.navigation_rail.selected_index
        for i, content_page in enumerate(self.content_area.controls):
            # update selected page
            if i == page_number:
                content_page.update_content()
            content_page.visible = page_number == i

    def build_navigation_rail(self):
        return NavigationRail(
            selected_index=0,
            label_type="none",
            on_change=self._navigation_change,
            # bgcolor=colors.SURFACE_VARIANT,
        )

    def update_destinations(self):
        self.navigation_rail.destinations = self.navigation_items
        self.navigation_rail.label_type = "all"

    def handle_resize(self, e):
        pass

    def set_content(self):
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

    def create_appbar(self) -> AppBar:
        appbar = AppBar(
            # leading=menu_button,
            # leading_width=40,
            # bgcolor=colors.SURFACE_VARIANT,
            toolbar_height=48,
            # elevation=8,
        )

        appbar.actions = [
            Row(
                [
                    IconButton(
                        icon=icons.HELP,
                    )
                ]
            )
        ]
        return appbar


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


def main(page: Page):

    pages = [
        (
            NavigationRailDestination(
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
            NavigationRailDestination(
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
            NavigationRailDestination(
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
    ]

    menu_layout = DesktopAppLayout(
        page=page,
        pages=pages,
        title="Basic Desktop App Layout",
        window_size=(1280, 720),
    )

    page.add(menu_layout)


if __name__ == "__main__":
    flet.app(
        target=main,
    )
