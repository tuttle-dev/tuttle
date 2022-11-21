import typing
from typing import Callable

from flet import (
    Column,
    Container,
    IconButton,
    NavigationRail,
    NavigationRailDestination,
    Row,
    UserControl,
    icons,
    padding,
)

from core.abstractions import LocalCache
from core.abstractions import TuttleView
from core.views.flet_constants import (
    CENTER_ALIGNMENT,
    CENTER_RAIL,
    COMPACT_RAIL_WIDTH,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
)
from res import spacing
from res.dimens import MIN_WINDOW_WIDTH
from .app_bar import get_app_bar
from .side_destinations import SideBarMenuItems, SideBarMenuItemsHandler


class HomeScreen(TuttleView, UserControl):
    def __init__(
        self,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        localCacheHandler: LocalCache,
    ):
        super().__init__(
            hasFloatingActionBtn=False,
            hasAppBar=True,
            onChangeRouteCallback=changeRouteCallback,
        )
        self.smi = SideBarMenuItemsHandler(
            localCacheHandler=localCacheHandler, onChangeRouteCallback=self.changeRoute
        )
        self.selected_tab = self.smi.first_item_index
        self.settings_icon = IconButton(
            icon=icons.SETTINGS_SUGGEST_OUTLINED,
            on_click=self.on_view_settings_clicked,
        )
        self.destination_rails = NavigationRail(
            selected_index=self.selected_tab,
            min_width=COMPACT_RAIL_WIDTH,
            extended=True,
            min_extended_width=int(MIN_WINDOW_WIDTH * 0.3),
            height=500,
            group_alignment=CENTER_RAIL,
            destinations=self.get_destinations(),
            on_change=self.on_destination_change,
        )
        initialDestination = self.get_destination_view_by_index(self.selected_tab)
        self.destination_body = Column(
            controls=[initialDestination],
            alignment=START_ALIGNMENT,
            horizontal_alignment=START_ALIGNMENT,
            expand=True,
        )

    def get_app_bar_if_any(self):
        return get_app_bar(on_click_notifications=self.on_view_notifications_clicked)

    def on_view_notifications_clicked(self, e):
        print("==TODO===")

    def on_view_settings_clicked(self, e):
        print("==TODO===")

    def get_destinations(self) -> list:
        """loops through the sidebar menu items and creates nav-rail-destinations"""
        items = []
        for item in SideBarMenuItems:
            itemDestination = NavigationRailDestination(
                icon=self.smi.get_side_bar_menu_item_icon(item),
                selected_icon=self.smi.get_side_bar_menu_item_selected_icon(item),
                label=self.smi.get_side_bar_menu_item_lbl(item),
                padding=padding.symmetric(
                    horizontal=spacing.SPACE_SM, vertical=spacing.SPACE_LG
                ),
            )
            items.append(itemDestination)
        return items

    def get_destination_view_by_index(self, menuItemIndex: int):
        menuItem = self.smi.get_side_bar_menu_item_from_index(menuItemIndex)
        destinationView = self.smi.get_destination_view_for_item(menuItem)
        return destinationView

    def on_destination_change(self, e):
        menuItemIndex = e.control.selected_index
        destinationView = self.get_destination_view_by_index(menuItemIndex)
        self.destination_body.controls.clear()
        self.destination_body.controls.append(destinationView)
        self.update()

    def build(self):
        """Called when page is built"""
        page_view = Row(
            [
                Container(
                    Column(
                        controls=[self.destination_rails, self.settings_icon],
                        alignment=SPACE_BETWEEN_ALIGNMENT,
                        horizontal_alignment=CENTER_ALIGNMENT,
                        spacing=spacing.SPACE_LG,
                    ),
                ),
                Container(
                    expand=True,
                    content=self.destination_body,
                ),
            ],
            spacing=0,
            alignment=START_ALIGNMENT,
            vertical_alignment=START_ALIGNMENT,
            expand=True,
        )
        page_view.padding = spacing.SPACE_STD
        return page_view
