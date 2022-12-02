from typing import Optional

from flet import (
    Card,
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
    ResponsiveRow,
    Icon,
)
from core.views import get_body_txt, get_headline_with_subtitle
from core.abstractions import DialogHandler, TuttleView
from core.constants_and_enums import (
    COMPACT_RAIL_WIDTH,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_START,
    ALWAYS_SCROLL,
    STRETCH_ALIGNMENT,
)
from res.colors import GRAY_DARK_COLOR, GRAY_COLOR, BLACK_COLOR
from res.dimens import (
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    SPACE_MD,
    SPACE_SM,
    SPACE_STD,
    SPACE_XL,
    SPACE_XS,
    SPACE_LG,
    TOOLBAR_HEIGHT,
)
from res.fonts import HEADLINE_4_SIZE, HEADLINE_FONT
from res.strings import PREFERENCES
from res.utils import (
    ADD_CLIENT_INTENT,
    ADD_CONTACT_INTENT,
    PREFERENCES_SCREEN_ROUTE,
    PROFILE_SCREEN_ROUTE,
)
from contacts.views.contact_editor import ContactEditorPopUp
from .home_top_bar import get_top_bar
from .main_menu import MainMenuItems, MainMenuItemsHandler
from .secondary_menu import SecondaryMenuHandler, SecondaryMenuItems

MIN_SIDE_BAR_WIDTH = int(MIN_WINDOW_WIDTH * 0.3)
MIN_FOOTER_WIDTH = int(MIN_WINDOW_WIDTH * 0.7)
MIN_BODY_HEIGHT = int(MIN_WINDOW_HEIGHT * 0.8)
NO_MENU_ITEM_INDEX = -1


def create_and_get_navigation_menu(
    title: str, on_change, selected_index: Optional[int] = None, destinations=[]
):
    return NavigationRail(
        leading=Container(
            content=Text(
                title,
                text_align=TXT_ALIGN_START,
                expand=True,
                font_family=HEADLINE_FONT,
                size=HEADLINE_4_SIZE,
                color=GRAY_DARK_COLOR,
            ),
            expand=True,
            width=MIN_SIDE_BAR_WIDTH,
            padding=padding.symmetric(horizontal=SPACE_STD),
            margin=margin.only(top=SPACE_STD),
        ),
        selected_index=selected_index,
        min_width=COMPACT_RAIL_WIDTH,
        extended=True,
        min_extended_width=MIN_SIDE_BAR_WIDTH,
        height=320,
        destinations=destinations,
        on_change=on_change,
    )


class HomeScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        on_navigate_back,
        local_storage,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            keep_back_stack=False,
            on_navigate_back=on_navigate_back,
        )
        self.main_menu_handler = MainMenuItemsHandler(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            local_storage=local_storage,
        )
        self.secondary_menu_handler = SecondaryMenuHandler(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            local_storage=local_storage,
        )

        self.selected_tab = NO_MENU_ITEM_INDEX
        self.settings_icon = IconButton(
            icon=icons.SETTINGS_SUGGEST_OUTLINED,
            on_click=self.on_view_settings_clicked,
            tooltip=PREFERENCES,
        )
        self.main_menu = create_and_get_navigation_menu(
            title=self.main_menu_handler.main_menu_title,
            destinations=self.get_main_menu_destinations(),
            on_change=self.on_main_menu_destination_change,
        )
        self.secondary_menu = create_and_get_navigation_menu(
            title=self.secondary_menu_handler.secondary_menu_title,
            destinations=self.get_secondary_menu_destinations(),
            on_change=self.on_secondary_menu_destination_change,
        )
        # initialize destination view with a welcome text
        self.destination_view = Container(
            padding=padding.all(SPACE_MD),
            content=Row(
                [
                    get_headline_with_subtitle(
                        title="Welcome back!",
                        subtitle="Select an item on the menu to get started",
                        subtitleColor=GRAY_COLOR,
                    )
                ]
            ),
        )
        self.dialog: Optional[DialogHandler] = None
        self.action_bar = get_top_bar(
            on_click_notifications_btn=self.on_view_notifications_clicked,
            on_click_new_btn=self.on_click_add_new,
            on_click_profile_btn=self.on_click_profile,
        )
        self.is_on_main_menu = True

    # MENU DESTINATIONS SETUP
    def get_main_menu_destinations(self) -> list:
        """loops through the main menu items and creates nav-rail-destinations"""
        items = []
        for item in MainMenuItems:
            itemDestination = NavigationRailDestination(
                icon_content=Icon(self.main_menu_handler.get_main_menu_item_icon(item)),
                selected_icon_content=Icon(
                    self.main_menu_handler.get_main_menu_item_selected_icon(item)
                ),
                label_content=get_body_txt(
                    self.main_menu_handler.get_main_menu_item_lbl(item)
                ),
                padding=padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_XS),
            )
            items.append(itemDestination)
        return items

    def get_secondary_menu_destinations(self) -> list:
        """loops through the secondary menu items and creates nav-rail-destinations"""
        items = []
        for item in SecondaryMenuItems:
            itemDestination = NavigationRailDestination(
                icon_content=Icon(
                    self.secondary_menu_handler.get_secondary_menu_item_icon(item)
                ),
                selected_icon=Icon(
                    self.secondary_menu_handler.get_secondary_menu_item_selected_icon(
                        item
                    )
                ),
                label_content=get_body_txt(
                    self.secondary_menu_handler.get_secondary_menu_item_lbl(item)
                ),
                padding=padding.symmetric(horizontal=SPACE_SM, vertical=SPACE_XS),
            )
            items.append(itemDestination)
        return items

    def set_main_menu_destination_view_by_index(
        self,
    ):
        if self.selected_tab == NO_MENU_ITEM_INDEX:
            return
        menu_item = self.main_menu_handler.get_main_menu_item_from_index(
            self.selected_tab
        )
        self.destination_view = (
            self.main_menu_handler.get_main_menu_destination_view_for_item(menu_item)
        )

    def on_main_menu_destination_change(self, e):
        if self.mounted:
            self.selected_tab = e.control.selected_index
            self.is_on_main_menu = True
            self.secondary_menu.selected_index = None
            self.set_main_menu_destination_view_by_index()
            self.destination_content_container.content = self.destination_view
            self.update()

    def on_secondary_menu_destination_change(self, e):
        if self.mounted:
            self.is_on_main_menu = False
            self.main_menu.selected_index = None
            self.show_snack("un implemented")
            self.update()

    # ACTION BUTTONS
    def on_click_add_new(self, e):
        if self.selected_tab == NO_MENU_ITEM_INDEX:
            return
        """determines the item user wishes to create e.g. new project / client"""
        item = None
        if self.is_on_main_menu:
            item = self.main_menu_handler.get_main_menu_item_from_index(
                self.selected_tab
            )
        else:
            item = self.secondary_menu_handler.get_secondary_menu_item_from_index(
                self.selected_tab
            )

        routeOrIntent = self.main_menu_handler.get_new_main_item_route_or_intent(item)
        if routeOrIntent == ADD_CLIENT_INTENT:
            self.pass_intent_to_destination(ADD_CLIENT_INTENT, "")

        elif routeOrIntent == ADD_CONTACT_INTENT:
            # show pop up for creating contact - TODO move this to contact
            if self.dialog:
                self.dialog.close_dialog()
            self.dialog = ContactEditorPopUp(
                dialog_controller=self.dialog_controller,
                on_submit=lambda data: self.pass_intent_to_destination(
                    ADD_CONTACT_INTENT, data
                ),
            )
            self.dialog.open_dialog()
        else:
            self.navigate_to_route(routeOrIntent)

    def pass_intent_to_destination(self, intent: str, data: str):
        if self.destination_view:
            self.destination_view.parent_intent_listener(intent, data)

    # RE ROUTING
    def on_view_notifications_clicked(self, e):
        print("==TODO===")

    def on_view_settings_clicked(self, e):
        self.navigate_to_route(PREFERENCES_SCREEN_ROUTE)

    def on_click_profile(self, e):
        self.navigate_to_route(PROFILE_SCREEN_ROUTE)

    def build(self):
        self.destination_content_container = Container(
            padding=padding.all(SPACE_MD),
            content=self.destination_view,
            margin=margin.only(bottom=SPACE_LG),
        )
        self.footer = Container(
            col={"xs": 12},
            content=Text("Tuttle 2022"),
            alignment=alignment.center,
            bgcolor=BLACK_COLOR,
            padding=padding.symmetric(vertical=SPACE_LG),
            margin=margin.only(top=SPACE_LG),
        )
        self.main_body = Column(
            col={
                "xs": 8,
                "md": 9,
                "lg": 10,
            },
            alignment=START_ALIGNMENT,
            horizontal_alignment=START_ALIGNMENT,
            controls=[
                self.action_bar,
                Card(self.destination_content_container),
            ],
        )

        self.view = Container(
            Column(
                [
                    ResponsiveRow(
                        controls=[
                            Container(
                                col={"xs": 4, "md": 3, "lg": 2},
                                padding=padding.only(top=SPACE_XL),
                                content=Column(
                                    controls=[
                                        self.main_menu,
                                        self.secondary_menu,
                                        Container(
                                            self.settings_icon,
                                            alignment=alignment.center,
                                            width=MIN_SIDE_BAR_WIDTH,
                                        ),
                                    ],
                                    alignment=SPACE_BETWEEN_ALIGNMENT,
                                    horizontal_alignment=START_ALIGNMENT,
                                    spacing=SPACE_LG,
                                ),
                            ),
                            self.main_body,
                        ],
                        spacing=0,
                        alignment=START_ALIGNMENT,
                        vertical_alignment=START_ALIGNMENT,
                        expand=1,
                    ),
                    self.footer,
                ],
                alignment=SPACE_BETWEEN_ALIGNMENT,
                horizontal_alignment=STRETCH_ALIGNMENT,
            ),
        )
        return self.view

    def did_mount(self):
        self.mounted = True

    def will_unmount(self):
        self.mounted = False
        if self.dialog:
            self.dialog.dimiss_open_dialogs()

    def on_window_resized(self, width, height):
        if not self.mounted:
            return
        super().on_window_resized(width, height)
        self.view.height = self.page_height
        DESTINATION_CONTENT_PERCENT_HEIGHT = 0.8 if self.page_height > 776 else 0.7
        self.destination_content_container.height = (
            self.page_height * DESTINATION_CONTENT_PERCENT_HEIGHT
        )
        self.update()
