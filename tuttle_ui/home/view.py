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
    FOOTER_HEIGHT,
)
from res.fonts import HEADLINE_4_SIZE, HEADLINE_FONT, BODY_2_SIZE

from res.utils import (
    ADD_CLIENT_INTENT,
    ADD_CONTACT_INTENT,
    PREFERENCES_SCREEN_ROUTE,
    PROFILE_SCREEN_ROUTE,
)
from contacts.view import ContactEditorPopUp
from typing import Callable

from flet import (
    Container,
    Text,
    padding,
    IconButton,
    Row,
    icons,
    alignment,
    ElevatedButton,
)

from core.constants_and_enums import SPACE_BETWEEN_ALIGNMENT, CENTER_ALIGNMENT
from core.views import get_app_logo, get_std_txt_field
from res.colors import BLACK_COLOR, WHITE_COLOR, PRIMARY_COLOR
from res.dimens import SPACE_MD, TOOLBAR_HEIGHT

from res.fonts import HEADLINE_4_SIZE, HEADLINE_FONT
from dataclasses import dataclass


from res.utils import (
    PROJECT_CREATOR_SCREEN_ROUTE,
    ADD_CLIENT_INTENT,
    ADD_CONTACT_INTENT,
    CONTRACT_CREATOR_SCREEN_ROUTE,
)
from core.abstractions import TuttleView
from typing import Optional
from clients.view import ClientsListView
from contacts.view import ContactsListView
from contracts.view import ContractsListView
from projects.view import ProjectsListView
from flet import icons, Container


MIN_SIDE_BAR_WIDTH = int(MIN_WINDOW_WIDTH * 0.3)
MIN_FOOTER_WIDTH = int(MIN_WINDOW_WIDTH * 0.7)
MIN_BODY_HEIGHT = int(MIN_WINDOW_HEIGHT * 0.8)
NO_MENU_ITEM_INDEX = -1


def get_top_bar(
    on_click_new_btn: Callable,
    on_click_notifications_btn: Callable,
    on_click_profile_btn: Callable,
):
    return Container(
        bgcolor=BLACK_COLOR,
        alignment=alignment.center,
        height=TOOLBAR_HEIGHT,
        padding=padding.symmetric(horizontal=SPACE_MD),
        content=Row(
            alignment=SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[
                Row(
                    controls=[
                        get_app_logo(width=10),
                        Text(
                            "Tuttle",
                            size=HEADLINE_4_SIZE,
                            font_family=HEADLINE_FONT,
                            color=WHITE_COLOR,
                        ),
                    ],
                    alignment=CENTER_ALIGNMENT,
                    vertical_alignment=CENTER_ALIGNMENT,
                ),
                Row(
                    controls=[
                        ElevatedButton(
                            text="New",
                            icon=icons.ADD_OUTLINED,
                            icon_color=PRIMARY_COLOR,
                            color=PRIMARY_COLOR,
                            on_click=on_click_new_btn,
                        ),
                        IconButton(
                            icons.NOTIFICATIONS,
                            icon_color=PRIMARY_COLOR,
                            icon_size=20,
                            tooltip="Notifications",
                            on_click=on_click_notifications_btn,
                        ),
                        IconButton(
                            icons.PERSON_OUTLINE_OUTLINED,
                            icon_color=PRIMARY_COLOR,
                            icon_size=20,
                            tooltip="Profile",
                            on_click=on_click_profile_btn,
                        ),
                    ]
                ),
            ],
        ),
    )


def create_and_get_navigation_menu(
    title: str,
    on_change,
    selected_index: Optional[int] = None,
    destinations=[],
    menu_height: int = 250,
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
        height=menu_height,
        min_extended_width=MIN_SIDE_BAR_WIDTH,
        destinations=destinations,
        on_change=on_change,
    )


@dataclass
class MenuItems:
    """defines a menu item"""

    index: int
    label: str
    icon: str
    selected_icon: str
    destination: TuttleView
    on_new_screen_route: Optional[str] = None
    on_new_intent: Optional[str] = None


class MainMenuItemsHandler:
    """Manages home's main-menu items"""

    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        local_storage,
    ):
        super().__init__()
        self.menu_title = "Work"
        self.projects_view = ProjectsListView(
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            navigate_to_route=navigate_to_route,
            local_storage=local_storage,
        )
        self.contacts_view = ContactsListView(
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            navigate_to_route=navigate_to_route,
            local_storage=local_storage,
        )
        self.clients_view = ClientsListView(
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            navigate_to_route=navigate_to_route,
            local_storage=local_storage,
        )
        self.contracts_view = ContractsListView(
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            navigate_to_route=navigate_to_route,
            local_storage=local_storage,
        )
        self.items = [
            MenuItems(
                0,
                "Projects",
                icons.WORK_OUTLINE,
                icons.WORK_ROUNDED,
                self.projects_view,
                on_new_screen_route=PROJECT_CREATOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
            MenuItems(
                1,
                "Contacts",
                icons.CONTACT_MAIL_OUTLINED,
                icons.CONTACT_MAIL_ROUNDED,
                self.contacts_view,
                on_new_screen_route=None,
                on_new_intent=ADD_CONTACT_INTENT,
            ),
            MenuItems(
                2,
                "Clients",
                icons.CONTACTS_OUTLINED,
                icons.CONTACTS_ROUNDED,
                self.clients_view,
                on_new_screen_route=None,
                on_new_intent=ADD_CLIENT_INTENT,
            ),
            MenuItems(
                3,
                "Contracts",
                icons.HANDSHAKE_OUTLINED,
                icons.HANDSHAKE_ROUNDED,
                self.contracts_view,
                on_new_screen_route=CONTRACT_CREATOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
        ]


class SecondaryMenuHandler:
    """Manages home's secondary side-menu items"""

    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        local_storage,
    ):
        super().__init__()
        self.menu_title = "Generate"
        self.items = [
            MenuItems(
                0,
                "Invoices",
                icons.ATTACH_MONEY_OUTLINED,
                icons.ATTACH_MONEY_ROUNDED,
                Container(),
                "/404",
            )
        ]


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
            page_scroll_type=None,
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
            tooltip="Preferences",
        )
        self.main_menu = create_and_get_navigation_menu(
            title=self.main_menu_handler.menu_title,
            destinations=self.get_menu_destinations(),
            on_change=lambda e: self.on_menu_destination_change(e),
        )
        self.secondary_menu = create_and_get_navigation_menu(
            title=self.secondary_menu_handler.menu_title,
            destinations=self.get_menu_destinations(menu_level=1),
            on_change=lambda e: self.on_menu_destination_change(e, menu_level=1),
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
        self.current_menu_handler = self.main_menu_handler

    # MENU DESTINATIONS SETUP
    def get_menu_destinations(self, menu_level=0) -> list:
        """loops through the main menu items and creates nav-rail-destinations"""
        items = []
        handler = (
            self.main_menu_handler if menu_level == 0 else self.secondary_menu_handler
        )
        for item in handler.items:
            itemDestination = NavigationRailDestination(
                icon_content=Icon(item.icon),
                selected_icon_content=Icon(item.selected_icon),
                label_content=get_body_txt(item.label, size=BODY_2_SIZE),
                padding=padding.symmetric(horizontal=SPACE_SM),
            )
            items.append(itemDestination)
        return items

    def on_menu_destination_change(self, e, menu_level=0):
        if self.mounted:
            # update the current menu
            self.current_menu_handler = (
                self.main_menu_handler
                if menu_level == 0
                else self.secondary_menu_handler
            )
            self.selected_tab = e.control.selected_index
            if self.selected_tab != NO_MENU_ITEM_INDEX:
                # update the destination view
                menu_item = self.current_menu_handler.items[self.selected_tab]
                self.destination_view = menu_item.destination
                self.destination_content_container.content = self.destination_view

            # clear selected items on the other menu
            if menu_level == 0:
                self.secondary_menu.selected_index = None
            else:
                self.main_menu.selected_index = None
                self.show_snack("un implemented")
            self.update()

    # ACTION BUTTONS
    def on_click_add_new(self, e):
        if self.selected_tab == NO_MENU_ITEM_INDEX:
            return
        """determine the item user wishes to create"""
        item = self.current_menu_handler.items[self.selected_tab]
        routeOrIntent = (
            item.on_new_screen_route if item.on_new_screen_route else item.on_new_intent
        )

        if routeOrIntent == ADD_CLIENT_INTENT:
            self.pass_intent_to_destination(ADD_CLIENT_INTENT, "")
        elif routeOrIntent == ADD_CONTACT_INTENT:
            # show pop up for creating contact
            self.pass_intent_to_destination(ADD_CONTACT_INTENT, "")
        else:
            self.navigate_to_route(routeOrIntent)

    def pass_intent_to_destination(self, intent: str, data: str):
        """forwards an intent to a child destination view"""
        if self.destination_view:
            self.destination_view.parent_intent_listener(intent, data)

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
            content=Text("Tuttle 2022", color=WHITE_COLOR),
            alignment=alignment.center,
            bgcolor=BLACK_COLOR,
            height=FOOTER_HEIGHT,
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
                                    alignment=START_ALIGNMENT,
                                    horizontal_alignment=START_ALIGNMENT,
                                    spacing=0,
                                    run_spacing=0,
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
        DESTINATION_CONTENT_PERCENT_HEIGHT = self.page_height - (
            self.action_bar.height + self.footer.height + 50
        )
        self.destination_content_container.height = DESTINATION_CONTENT_PERCENT_HEIGHT
        self.update()
