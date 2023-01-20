from typing import Callable, Optional

import webbrowser
from dataclasses import dataclass
from .intent import HomeIntent
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
from core import utils, views
from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from invoicing.view import InvoicingListView
from projects.view import ProjectsListView
from res import colors, dimens, fonts, res_utils, theme
from timetracking.view import TimeTrackingView

MIN_SIDE_BAR_WIDTH = int(dimens.MIN_WINDOW_WIDTH * 0.3)
MIN_FOOTER_WIDTH = int(dimens.MIN_WINDOW_WIDTH * 0.7)
MIN_BODY_HEIGHT = int(dimens.MIN_WINDOW_HEIGHT * 0.8)
NO_MENU_ITEM_INDEX = -1


def get_action_bar(
    on_click_new_btn: Callable,
    on_click_notifications_btn: Callable,
    on_click_profile_btn: Callable,
    on_view_settings_clicked: Callable,
):
    """
    Returns the action bar containing various buttons for application functionality.

    :param on_click_new_btn: Callable function to be called when the 'New' button is clicked.
    :param on_click_notifications_btn: Callable function to be called when the 'Notifications' button is clicked.
    :param on_click_profile_btn: Callable function to be called when the 'Profile' button is clicked.
    :param on_view_settings_clicked: Callable function to be called when the 'Settings' button is clicked.
    :return: A Container widget containing the action bar.
    """
    return Container(
        alignment=alignment.center,
        height=dimens.TOOLBAR_HEIGHT,
        padding=padding.symmetric(horizontal=dimens.SPACE_MD),
        border=border.only(bottom=border.BorderSide(width=1)),
        content=Row(
            alignment=utils.SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=utils.CENTER_ALIGNMENT,
            controls=[
                Row(
                    controls=[
                        views.get_heading(
                            "Tuttle",
                            size=fonts.HEADLINE_4_SIZE,
                        )
                    ],
                    alignment=utils.CENTER_ALIGNMENT,
                    vertical_alignment=utils.CENTER_ALIGNMENT,
                ),
                Row(
                    controls=[
                        ElevatedButton(
                            text="New",
                            icon=icons.ADD_OUTLINED,
                            icon_color=colors.PRIMARY_COLOR,
                            color=colors.PRIMARY_COLOR,
                            on_click=on_click_new_btn,
                        ),
                        # TODO: Implement notifications
                        # IconButton(
                        #     icons.NOTIFICATIONS,
                        #     icon_color=colors.PRIMARY_COLOR,
                        #     icon_size=dimens.ICON_SIZE,
                        #     tooltip="Notifications",
                        #     on_click=on_click_notifications_btn,
                        # ),
                        IconButton(
                            icon=icons.SETTINGS_SUGGEST_OUTLINED,
                            icon_color=colors.PRIMARY_COLOR,
                            icon_size=dimens.ICON_SIZE,
                            on_click=on_view_settings_clicked,
                            tooltip="Preferences",
                        ),
                        IconButton(
                            icons.PERSON_OUTLINE_OUTLINED,
                            icon_color=colors.PRIMARY_COLOR,
                            icon_size=dimens.ICON_SIZE,
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
    """
    Returns a navigation menu for the application.

    :param title: Title of the navigation menu.
    :param on_change: Callable function to be called when the selected item in the menu changes.
    :param selected_index: The index of the selected item in the menu.
    :param destinations: List of destinations in the menu.
    :param menu_height: The height of the menu.
    :return: A NavigationRail widget containing the navigation menu.
    """
    return NavigationRail(
        leading=Container(
            content=views.get_sub_heading_txt(
                subtitle=title,
                align=utils.START_ALIGNMENT,
                expand=True,
                color=colors.GRAY_DARK_COLOR,
            ),
            expand=True,
            width=MIN_SIDE_BAR_WIDTH,
            margin=margin.only(top=dimens.SPACE_STD),
            padding=padding.only(left=dimens.SPACE_STD),
        ),
        selected_index=selected_index,
        min_width=utils.COMPACT_RAIL_WIDTH,
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
            # MenuItem(
            #     index=0,
            #     label="Dashboard",
            #     icon=utils.TuttleComponentIcons.dashboard_icon,
            #     selected_icon=utils.TuttleComponentIcons.dashboard_selected_icon,
            #     destination=Container(),
            #     on_new_screen_route="/404",
            # ),
            MenuItem(
                index=1,
                label="Projects",
                icon=utils.TuttleComponentIcons.project_icon,
                selected_icon=utils.TuttleComponentIcons.project_selected_icon,
                destination=self.projects_view,
                on_new_screen_route=res_utils.PROJECT_EDITOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
            MenuItem(
                index=4,
                label="Contracts",
                icon=utils.TuttleComponentIcons.contract_icon,
                selected_icon=utils.TuttleComponentIcons.contract_selected_icon,
                destination=self.contracts_view,
                on_new_screen_route=res_utils.CONTRACT_EDITOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
            MenuItem(
                index=3,
                label="Clients",
                icon=utils.TuttleComponentIcons.client_icon,
                selected_icon=utils.TuttleComponentIcons.client_selected_icon,
                destination=self.clients_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.ADD_CLIENT_INTENT,
            ),
            MenuItem(
                index=2,
                label="Contacts",
                icon=utils.TuttleComponentIcons.contact_icon,
                selected_icon=utils.TuttleComponentIcons.contact_selected_icon,
                destination=self.contacts_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.ADD_CONTACT_INTENT,
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
                icon=utils.TuttleComponentIcons.timetracking_icon,
                selected_icon=utils.TuttleComponentIcons.timetracking_selected_icon,
                destination=self.timetrack_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.NEW_TIME_TRACK_INTENT,
            ),
            MenuItem(
                index=1,
                label="Invoicing",
                icon=utils.TuttleComponentIcons.invoicing_icon,
                selected_icon=utils.TuttleComponentIcons.invoicing_selected_icon,
                destination=self.invoicing_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.CREATE_INVOICE_INTENT,
            ),
        ]


class HomeScreen(TuttleView, UserControl):
    def __init__(
        self,
        params: TuttleViewParams,
    ):
        super().__init__(params)
        self.keep_back_stack = False
        self.page_scroll_type = None
        self.main_menu_handler = MainMenuItemsHandler(params)
        self.secondary_menu_handler = SecondaryMenuHandler(params)
        self.intent_handler = HomeIntent(local_storage=params.local_storage)
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
            padding=padding.all(dimens.SPACE_MD),
            content=Row(
                [
                    views.get_heading_with_subheading(
                        title="Welcome back!",
                        subtitle="Select an item on the menu to get started",
                        subtitle_color=colors.GRAY_COLOR,
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
                icon_content=Icon(
                    item.icon,
                    size=dimens.ICON_SIZE,
                ),
                selected_icon_content=Icon(
                    item.selected_icon,
                    size=dimens.ICON_SIZE,
                ),
                label_content=views.get_body_txt(item.label),
                padding=padding.symmetric(horizontal=dimens.SPACE_SM),
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
            self.update_self()

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

    def on_resume_after_back_pressed(self):
        if self.destination_view and isinstance(self.destination_view, TuttleView):
            self.destination_view.on_resume_after_back_pressed()

    def pass_intent_to_destination(self, intent: str, data: str):
        """forwards an intent to a child destination view"""
        if self.destination_view and isinstance(self.destination_view, TuttleView):
            self.destination_view.parent_intent_listener(intent, data)

    def on_view_notifications_clicked(self, e):
        self.show_snack("not implemented", True)

    def on_view_settings_clicked(self, e):
        self.navigate_to_route(res_utils.PREFERENCES_SCREEN_ROUTE)

    def on_click_profile(self, e):
        self.navigate_to_route(res_utils.PROFILE_SCREEN_ROUTE)

    def build(self):
        self.destination_content_container = Container(
            padding=padding.all(dimens.SPACE_MD),
            content=self.destination_view,
            margin=margin.only(bottom=dimens.SPACE_LG),
        )
        self.footer = Container(
            col={"xs": 12},
            content=views.get_heading(),
            alignment=alignment.center,
            border=border.only(top=border.BorderSide(1, "black")),
            height=dimens.FOOTER_HEIGHT,
        )
        self.main_body = Column(
            col={
                "xs": 8,
                "md": 9,
                "lg": 10,
            },
            alignment=utils.START_ALIGNMENT,
            horizontal_alignment=utils.START_ALIGNMENT,
            controls=[
                self.action_bar,
                self.destination_content_container,
            ],
        )
        self.side_bar = Container(
            col={"xs": 4, "md": 3, "lg": 2},
            padding=padding.only(top=dimens.SPACE_XL),
            content=Column(
                controls=[
                    self.main_menu,
                    self.secondary_menu,
                ],
                alignment=utils.START_ALIGNMENT,
                horizontal_alignment=utils.START_ALIGNMENT,
                spacing=0,
                run_spacing=0,
            ),
            border=border.only(right=border.BorderSide(width=1)),
        )

        self.view = Container(
            Column(
                [
                    ResponsiveRow(
                        controls=[
                            self.side_bar,
                            self.main_body,
                        ],
                        spacing=0,
                        alignment=utils.START_ALIGNMENT,
                        vertical_alignment=utils.START_ALIGNMENT,
                        expand=1,
                    ),
                    self.footer,
                ],
                alignment=utils.SPACE_BETWEEN_ALIGNMENT,
                horizontal_alignment=utils.STRETCH_ALIGNMENT,
                spacing=0,
                run_spacing=0,
            ),
        )
        return self.view

    def did_mount(self):
        self.mounted = True
        self.load_preferred_theme()

    def on_resume_after_back_pressed(self):
        self.load_preferred_theme()

    def load_preferred_theme(self):
        result = self.intent_handler.get_preferred_theme()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)
            return
        self.preferred_theme = result.data
        side_bar_components = [
            self.side_bar,
            self.main_menu,
            self.secondary_menu,
        ]
        side_bar_bg_color = colors.BLACK_COLOR_ALT  # default is dark mode
        self.action_bar.bgcolor = colors.BLACK_COLOR
        if self.preferred_theme == theme.THEME_MODES.light.value:
            side_bar_bg_color = colors.GRAY_LIGHT_COLOR
            self.action_bar.bgcolor = colors.WHITE_COLOR_ALT
        for component in side_bar_components:
            component.bgcolor = side_bar_bg_color

        self.update_self()

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
        self.update_self()
