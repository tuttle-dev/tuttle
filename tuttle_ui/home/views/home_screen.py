import typing
from typing import Callable, Optional

from flet import (
    Column,
    Container,
    IconButton,
    NavigationRail,
    NavigationRailDestination,
    Row,
    Text,
    UserControl,
    alignment,
    icons,
    margin,
    padding,
)

from core.abstractions import DialogHandler
from clients.view.client_creator import NewClientPopUp
from contacts.view.contact_creator import NewContactPopUp
from core.abstractions import LocalCache, TuttleView
from core.views.flet_constants import (
    COMPACT_RAIL_WIDTH,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_START,
)
from res import spacing
from res.colors import GRAY_DARK_COLOR
from res.dimens import MIN_WINDOW_WIDTH
from res.fonts import HEADLINE_3_SIZE, HEADLINE_FONT
from res.strings import PREFERENCES
from res.utils import ADD_CLIENT_INTENT, ADD_CONTACT_INTENT

from .action_bar import get_action_bar
from .side_destinations import SideBarMenuItems, SideBarMenuItemsHandler

MIN_SIDE_BAR_WIDTH = int(MIN_WINDOW_WIDTH * 0.3)


class HomeScreen(TuttleView, UserControl):
    def __init__(
        self,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        localCacheHandler: LocalCache,
        dialogController: Callable,
        showSnackCallback: Callable,
    ):
        super().__init__(
            hasAppBar=False,
            onChangeRouteCallback=changeRouteCallback,
            pageDialogController=dialogController,
            showSnackCallback=showSnackCallback,
        )
        self.smi = SideBarMenuItemsHandler(
            localCacheHandler=localCacheHandler,
            onChangeRouteCallback=self.changeRoute,
            pageDialogController=self.pageDialogController,
            showSnackCallback=self.showSnack,
        )

        self.selected_tab = self.smi.first_item_index
        self.settings_icon = IconButton(
            icon=icons.SETTINGS_SUGGEST_OUTLINED,
            on_click=self.on_view_settings_clicked,
            tooltip=PREFERENCES,
        )
        self.destination_rails = NavigationRail(
            leading=Container(
                content=Text(
                    self.smi.mainMenuTitle,
                    text_align=TXT_ALIGN_START,
                    expand=True,
                    font_family=HEADLINE_FONT,
                    size=HEADLINE_3_SIZE,
                    color=GRAY_DARK_COLOR,
                ),
                expand=True,
                width=MIN_SIDE_BAR_WIDTH,
                padding=padding.symmetric(horizontal=spacing.SPACE_STD),
                margin=margin.only(top=spacing.SPACE_STD),
            ),
            selected_index=self.selected_tab,
            min_width=COMPACT_RAIL_WIDTH,
            extended=True,
            min_extended_width=MIN_SIDE_BAR_WIDTH,
            height=500,
            destinations=self.get_main_menu_destinations(),
            on_change=self.on_main_menu_destination_change,
        )
        initialDestination = self.get_main_menu_destination_view_by_index(
            self.selected_tab
        )
        self.destination_body = Column(
            controls=[initialDestination],
            alignment=START_ALIGNMENT,
            horizontal_alignment=START_ALIGNMENT,
            expand=True,
        )
        self.dialog: Optional[DialogHandler] = None

    def get_action_bar(self):
        return get_action_bar(
            onClickNotifications=self.on_view_notifications_clicked,
            onClickNew=self.on_click_add,
            onClickProfile=self.on_click_profile,
        )

    def on_view_notifications_clicked(self, e):
        print("==TODO===")

    def on_view_settings_clicked(self, e):
        print("==TODO===")

    def on_click_profile(self, e):
        print("==TODO===")

    def on_click_add(self, e):
        """determines the item user wishes to create e.g. new project / client"""
        item = self.smi.get_side_bar_menu_item_from_index(self.selected_tab)
        routeOrIntent = self.smi.get_new_item_route_or_intent(item)
        if routeOrIntent == ADD_CLIENT_INTENT:
            # show pop up for creating client
            if self.dialog:
                self.dialog.close_dialog()
            self.dialog = NewClientPopUp(
                dialogController=self.pageDialogController,
                onSubmit=lambda data: self.pass_intent_to_destination(
                    ADD_CLIENT_INTENT, data
                ),
            )
            self.dialog.open_dialog()

        elif routeOrIntent == ADD_CONTACT_INTENT:
            # show pop up for creating contact
            if self.dialog:
                self.dialog.close_dialog()
            self.dialog = NewContactPopUp(
                dialogController=self.pageDialogController,
                onSubmit=lambda data: self.pass_intent_to_destination(
                    ADD_CONTACT_INTENT, data
                ),
            )
            self.dialog.open_dialog()
        else:
            self.changeRoute(routeOrIntent, None)

    def pass_intent_to_destination(self, intent: str, data: str):
        if self.destinationView:
            self.destinationView.parent_intent_listener(intent, data)

    def get_main_menu_destinations(self) -> list:
        """loops through the sidebar menu items and creates nav-rail-destinations"""
        items = []
        for item in SideBarMenuItems:
            itemDestination = NavigationRailDestination(
                icon=self.smi.get_side_bar_menu_item_icon(item),
                selected_icon=self.smi.get_side_bar_menu_item_selected_icon(item),
                label=self.smi.get_side_bar_menu_item_lbl(item),
                padding=padding.symmetric(
                    horizontal=spacing.SPACE_SM, vertical=spacing.SPACE_XS
                ),
            )
            items.append(itemDestination)
        return items

    def get_main_menu_destination_view_by_index(self, menuItemIndex: int):
        menuItem = self.smi.get_side_bar_menu_item_from_index(menuItemIndex)
        self.destinationView = self.smi.get_destination_view_for_item(menuItem)
        return self.destinationView

    def on_main_menu_destination_change(self, e):
        self.selected_tab = e.control.selected_index
        destinationView = self.get_main_menu_destination_view_by_index(
            self.selected_tab
        )
        self.destination_body.controls.clear()
        self.destination_body.controls.append(destinationView)
        self.update()

    def build(self):
        """Called when page is built"""
        page_view = Row(
            [
                Container(
                    padding=padding.only(top=spacing.SPACE_XL),
                    content=Column(
                        controls=[
                            self.destination_rails,
                            Container(
                                self.settings_icon,
                                alignment=alignment.center,
                                width=MIN_SIDE_BAR_WIDTH,
                            ),
                        ],
                        alignment=SPACE_BETWEEN_ALIGNMENT,
                        horizontal_alignment=START_ALIGNMENT,
                        spacing=spacing.SPACE_LG,
                    ),
                ),
                Column(
                    expand=True,
                    controls=[
                        self.get_action_bar(),
                        Container(content=self.destination_body),
                    ],
                ),
            ],
            spacing=0,
            alignment=START_ALIGNMENT,
            vertical_alignment=START_ALIGNMENT,
            expand=True,
        )
        page_view.padding = spacing.SPACE_STD
        return page_view

    def will_unmount(self):
        try:
            self.dialog.dimiss_open_dialogs()
        except Exception as e:
            print(e)
