from typing import Callable, Optional

import webbrowser
from dataclasses import dataclass

from flet import (
    Column,
    Container,
    ElevatedButton,
    Icon,
    IconButton,
    NavigationRail,
    NavigationRailDestination,
    PopupMenuButton,
    PopupMenuItem,
    ResponsiveRow,
    Row,
    Text,
    UserControl,
    alignment,
    border,
    icons,
    margin,
    padding,
)

from clients.view import ClientsListView
from contacts.view import ContactEditorPopUp, ContactsListView
from contracts.view import ContractsListView
from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from core.utils import (
    ALWAYS_SCROLL,
    CENTER_ALIGNMENT,
    COMPACT_RAIL_WIDTH,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    STRETCH_ALIGNMENT,
    TXT_ALIGN_START,
)
from core.views import (
    get_app_logo,
    get_body_txt,
    get_headline_with_subtitle,
    get_std_txt_field,
)
from invoicing.view import InvoicingListView
from projects.view import ProjectsListView
from res.colors import (
    BLACK_COLOR,
    GRAY_COLOR,
    GRAY_DARK_COLOR,
    PRIMARY_COLOR,
    WHITE_COLOR,
)
from res.dimens import (
    FOOTER_HEIGHT,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_STD,
    SPACE_XL,
    TOOLBAR_HEIGHT,
)
from res.fonts import (
    BODY_2_SIZE,
    HEADLINE_4_SIZE,
    HEADLINE_FONT,
    SUBTITLE_2_SIZE,
)
from res import res_utils
from timetracking.view import TimeTrackingView

MIN_SIDE_BAR_WIDTH = int(MIN_WINDOW_WIDTH * 0.3)
MIN_FOOTER_WIDTH = int(MIN_WINDOW_WIDTH * 0.7)
MIN_BODY_HEIGHT = int(MIN_WINDOW_HEIGHT * 0.8)
NO_MENU_ITEM_INDEX = -1


def get_action_bar(
    on_click_new_btn: Callable,
    on_click_notifications_btn: Callable,
    on_click_profile_btn: Callable,
    on_view_settings_clicked: Callable,
):
    return Container(
        alignment=alignment.center,
        height=TOOLBAR_HEIGHT,
        padding=padding.symmetric(horizontal=SPACE_MD),
        border=border.only(bottom=border.BorderSide(width=1)),
        content=Row(
            alignment=SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[
                Row(
                    controls=[
                        # TODO: replace with actual app logo
                        # get_app_logo(width=10),
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
                            icon=icons.SETTINGS_SUGGEST_OUTLINED,
                            icon_color=PRIMARY_COLOR,
                            icon_size=20,
                            on_click=on_view_settings_clicked,
                            tooltip="Preferences",
                        ),
                        IconButton(
                            icons.PERSON_OUTLINE_OUTLINED,
                            icon_color=PRIMARY_COLOR,
                            icon_size=20,
                            tooltip="Profile",
                            on_click=on_click_profile_btn,
                        ),
                        PopupMenuButton(
                            icon=icons.HELP,
                            items=[
                                PopupMenuItem(
                                    icon=icons.CONTACT_SUPPORT,
                                    text="Ask a question",
                                    on_click=lambda _: webbrowser.open(
                                        "https://github.com/tuttle-dev/tuttle/discussions"
                                    ),
                                ),
                                PopupMenuItem(
                                    icon=icons.BUG_REPORT,
                                    text="Report a bug",
                                    on_click=lambda _: webbrowser.open(
                                        "https://github.com/tuttle-dev/tuttle/issues"
                                    ),
                                ),
                            ],
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
    menu_height: int = 300,
):
    return NavigationRail(
        leading=Container(
            content=Text(
                title,
                text_align=START_ALIGNMENT,
                expand=True,
                font_family=SUBTITLE_2_SIZE,
                size=HEADLINE_4_SIZE,
                color=GRAY_DARK_COLOR,
            ),
            expand=True,
            width=MIN_SIDE_BAR_WIDTH,
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
class MenuItem:
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

    def __init__(self, params: TuttleViewParams):
        super().__init__()
        self.menu_title = "My Business"
        self.projects_view = ProjectsListView(params)
        self.contacts_view = ContactsListView(params)
        self.clients_view = ClientsListView(params)
        self.contracts_view = ContractsListView(params)
        self.items = [
            MenuItem(
                index=0,
                label="Dashboard",
                icon=icons.SPEED,
                selected_icon=icons.SPEED_ROUNDED,
                destination=Container(),
                on_new_screen_route="/404",
            ),
            MenuItem(
                index=1,
                label="Projects",
                icon=icons.WORK_OUTLINE,
                selected_icon=icons.WORK_ROUNDED,
                destination=self.projects_view,
                on_new_screen_route=res_utils.PROJECT_CREATOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
            MenuItem(
                index=2,
                label="Contacts",
                icon=icons.CONTACT_MAIL_OUTLINED,
                selected_icon=icons.CONTACT_MAIL_ROUNDED,
                destination=self.contacts_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.ADD_CONTACT_INTENT,
            ),
            MenuItem(
                index=3,
                label="Clients",
                icon=icons.CONTACTS_OUTLINED,
                selected_icon=icons.CONTACTS_ROUNDED,
                destination=self.clients_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.ADD_CLIENT_INTENT,
            ),
            MenuItem(
                index=4,
                label="Contracts",
                icon=icons.HANDSHAKE_OUTLINED,
                selected_icon=icons.HANDSHAKE_ROUNDED,
                destination=self.contracts_view,
                on_new_screen_route=res_utils.CONTRACT_CREATOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
        ]


class SecondaryMenuHandler:
    """Manages home's secondary side-menu items"""

    def __init__(self, params: TuttleViewParams):
        super().__init__()
        self.menu_title = "Workflows"

        self.timetrack_view = TimeTrackingView(params)
        self.invoicing_view = InvoicingListView(params)

        self.items = [
            MenuItem(
                index=0,
                label="Time Tracking",
                icon=icons.TIMER_OUTLINED,
                selected_icon=icons.TIMER_ROUNDED,
                destination=self.timetrack_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.NEW_TIME_TRACK_INTENT,
            ),
            MenuItem(
                index=1,
                label="Invoicing",
                icon=icons.ATTACH_MONEY_SHARP,
                selected_icon=icons.ATTACH_MONEY_ROUNDED,
                destination=self.invoicing_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.CREATE_INVOICE_INTENT,
            ),
            MenuItem(
                index=2,
                label="Datatable",
                icon=icons.TABLE_CHART,
                selected_icon=icons.TABLE_CHART_ROUNDED,
                destination=Container(),
                on_new_screen_route="/404",
            ),
        ]


class HomeScreen(TuttleView, UserControl):
    def __init__(self, params: TuttleViewParams):
        super().__init__(params)
        self.keep_back_stack = False
        self.page_scroll_type = None
        self.main_menu_handler = MainMenuItemsHandler(params)
        self.secondary_menu_handler = SecondaryMenuHandler(params)

        self.selected_tab = NO_MENU_ITEM_INDEX

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
        self.action_bar = get_action_bar(
            on_click_notifications_btn=self.on_view_notifications_clicked,
            on_click_new_btn=self.on_click_add_new,
            on_click_profile_btn=self.on_click_profile,
            on_view_settings_clicked=self.on_view_settings_clicked,
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
            self.update()

    # ACTION BUTTONS
    def on_click_add_new(self, e):
        if self.selected_tab == NO_MENU_ITEM_INDEX:
            return
        """determine the item user wishes to create"""
        item = self.current_menu_handler.items[self.selected_tab]
        if item.on_new_intent:
            self.pass_intent_to_destination(item.on_new_intent, "")
        else:
            self.navigate_to_route(item.on_new_screen_route)

    def pass_intent_to_destination(self, intent: str, data: str):
        """forwards an intent to a child destination view"""
        if self.destination_view:
            self.destination_view.parent_intent_listener(intent, data)

    def on_view_notifications_clicked(self, e):
        self.show_snack("not implemented", True)

    def on_view_settings_clicked(self, e):
        self.navigate_to_route(res_utils.PREFERENCES_SCREEN_ROUTE)

    def on_click_profile(self, e):
        self.navigate_to_route(res_utils.PROFILE_SCREEN_ROUTE)

    def build(self):
        self.destination_content_container = Container(
            padding=padding.all(SPACE_MD),
            content=self.destination_view,
            margin=margin.only(bottom=SPACE_LG),
        )
        self.footer = Container(
            col={"xs": 12},
            content=Text(""),
            alignment=alignment.center,
            border=border.only(top=border.BorderSide(1, "black")),
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
                self.destination_content_container,
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
                                    ],
                                    alignment=START_ALIGNMENT,
                                    horizontal_alignment=START_ALIGNMENT,
                                    spacing=0,
                                    run_spacing=0,
                                ),
                                border=border.only(right=border.BorderSide(width=1)),
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

    def on_window_resized_listener(self, width, height):
        if not self.mounted:
            return
        super().on_window_resized_listener(width, height)
        self.view.height = self.page_height
        DESTINATION_CONTENT_PERCENT_HEIGHT = self.page_height - (
            self.action_bar.height + self.footer.height + 50
        )
        self.destination_content_container.height = DESTINATION_CONTENT_PERCENT_HEIGHT
        self.update()
