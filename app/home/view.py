from typing import Callable, Optional

import webbrowser
from dataclasses import dataclass

from flet import (
    Column,
    Container,
    ElevatedButton,
    Icon,
    IconButton,
    NavigationRailDestination,
    PopupMenuButton,
    PopupMenuItem,
    ResponsiveRow,
    Row,
    UserControl,
    alignment,
    border,
    icons,
    padding,
)

from clients.view import ClientsListView
from contacts.view import ContactsListView
from contracts.view import ContractsListView
from core import utils, views
from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from invoicing.view import InvoicingListView
from projects.view import ProjectsListView
from res import colors, dimens, fonts, res_utils, theme
from timetracking.view import TimeTrackingView

from preferences.intent import PreferencesIntent


MIN_FOOTER_WIDTH = int(dimens.MIN_WINDOW_WIDTH * 0.7)
MIN_BODY_HEIGHT = int(dimens.MIN_WINDOW_HEIGHT * 0.8)


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
        border=border.only(
            bottom=border.BorderSide(
                width=0.2,
                color=colors.BORDER_DARK_COLOR,
            )
        ),
        content=Row(
            alignment=utils.SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=utils.CENTER_ALIGNMENT,
            controls=[
                Row(
                    controls=[
                        views.get_heading(
                            "",
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
                            icon_size=dimens.ICON_SIZE,
                            on_click=on_view_settings_clicked,
                            tooltip="Preferences",
                        ),
                        IconButton(
                            icons.PERSON_OUTLINE_OUTLINED,
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
            views.NavigationMenuItem(
                index=1,
                label="Projects",
                icon=utils.TuttleComponentIcons.project_icon,
                selected_icon=utils.TuttleComponentIcons.project_selected_icon,
                destination=self.projects_view,
                on_new_screen_route=res_utils.PROJECT_EDITOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
            views.NavigationMenuItem(
                index=4,
                label="Contracts",
                icon=utils.TuttleComponentIcons.contract_icon,
                selected_icon=utils.TuttleComponentIcons.contract_selected_icon,
                destination=self.contracts_view,
                on_new_screen_route=res_utils.CONTRACT_EDITOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
            views.NavigationMenuItem(
                index=3,
                label="Clients",
                icon=utils.TuttleComponentIcons.client_icon,
                selected_icon=utils.TuttleComponentIcons.client_selected_icon,
                destination=self.clients_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.ADD_CLIENT_INTENT,
            ),
            views.NavigationMenuItem(
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
            views.NavigationMenuItem(
                index=0,
                label="Time Tracking",
                icon=utils.TuttleComponentIcons.timetracking_icon,
                selected_icon=utils.TuttleComponentIcons.timetracking_selected_icon,
                destination=self.timetrack_view,
                on_new_screen_route=None,
                on_new_intent=res_utils.NEW_TIME_TRACK_INTENT,
            ),
            views.NavigationMenuItem(
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
    """The home screen"""

    def __init__(
        self,
        params: TuttleViewParams,
    ):
        super().__init__(params)
        self.keep_back_stack = False
        self.page_scroll_type = None
        self.main_menu_handler = MainMenuItemsHandler(params)
        self.secondary_menu_handler = SecondaryMenuHandler(params)
        self.preferences_intent = PreferencesIntent(
            client_storage=params.client_storage
        )
        self.selected_tab = 0

        self.main_menu = views.get_std_navigation_menu(
            title=self.main_menu_handler.menu_title,
            destinations=self.get_menu_destinations(),
            on_change=lambda e: self.on_menu_destination_change(e),
        )
        self.secondary_menu = views.get_std_navigation_menu(
            title=self.secondary_menu_handler.menu_title,
            destinations=self.get_menu_destinations(menu_level=1),
            on_change=lambda e: self.on_menu_destination_change(e, menu_level=1),
        )
        self.current_menu_handler = self.main_menu_handler
        self.destination_view = self.current_menu_handler.items[0].destination
        self.dialog: Optional[DialogHandler] = None
        self.action_bar = get_action_bar(
            on_click_notifications_btn=self.on_view_notifications_clicked,
            on_click_new_btn=self.on_click_add_new,
            on_click_profile_btn=self.on_click_profile,
            on_view_settings_clicked=self.on_view_settings_clicked,
        )

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
        """handles the menu destination change event"""
        if self.mounted:
            # update the current menu
            self.current_menu_handler = (
                self.main_menu_handler
                if menu_level == 0
                else self.secondary_menu_handler
            )
            self.selected_tab = e.control.selected_index

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
        """handles the add new button click event"""
        if self.selected_tab == NO_MENU_ITEM_INDEX:
            return
        """determine the item user wishes to create"""
        item = self.current_menu_handler.items[self.selected_tab]
        if item.on_new_intent:
            self.pass_intent_to_destination(item.on_new_intent)
        else:
            self.navigate_to_route(item.on_new_screen_route)

    def on_resume_after_back_pressed(self):
        """called when the user presses the back button"""
        if self.destination_view and isinstance(self.destination_view, TuttleView):
            self.destination_view.on_resume_after_back_pressed()

    def pass_intent_to_destination(self, intent: str, data: Optional[any] = None):
        """pass an intent to the destination view"""
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
        )
        self.footer = Container(
            col={"xs": 12},
            content=views.get_heading(),
            alignment=alignment.center,
            border=border.only(
                top=border.BorderSide(width=0.2, color=colors.BORDER_DARK_COLOR)
            ),
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
            border=border.only(
                right=border.BorderSide(
                    width=0.2,
                    color=colors.BORDER_DARK_COLOR,
                )
            ),
        )

        self.home_screen_view = Container(
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
        return self.home_screen_view

    def did_mount(self):
        self.mounted = True
        self.load_preferred_theme()

    def on_resume_after_back_pressed(self):
        self.load_preferred_theme()
        self.pass_intent_to_destination(res_utils.RELOAD_INTENT)

    def load_preferred_theme(self):
        """Sets the UI theme from the user's preferences"""
        result = self.preferences_intent.get_preferred_theme()
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, is_error=True)
            return
        self.preferred_theme = result.data
        side_bar_components = [
            self.side_bar,
            self.main_menu,
            self.secondary_menu,
        ]
        side_bar_bg_color = colors.SIDEBAR_DARK_COLOR  # default is dark mode
        self.action_bar.bgcolor = colors.ACTION_BAR_DARK_COLOR
        if self.preferred_theme == theme.THEME_MODES.light.value:
            side_bar_bg_color = colors.SIDEBAR_LIGHT_COLOR
            self.action_bar.bgcolor = colors.ACTION_BAR_LIGHT_COLOR
        for component in side_bar_components:
            component.bgcolor = side_bar_bg_color
        self.footer.bgcolor = side_bar_bg_color  # footer and side bar have same bgcolor
        self.update_self()

    def on_window_resized_listener(self, width, height):
        if not self.mounted:
            return
        super().on_window_resized_listener(width, height)
        self.home_screen_view.height = self.page_height
        DESTINATION_CONTENT_PERCENT_HEIGHT = self.page_height - (
            self.action_bar.height + self.footer.height + 50
        )
        self.destination_content_container.height = DESTINATION_CONTENT_PERCENT_HEIGHT
        self.update_self()

    def will_unmount(self):
        self.mounted = False
        if self.dialog:
            self.dialog.dimiss_open_dialogs()
