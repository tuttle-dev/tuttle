from enum import Enum
from res.strings import (
    PROJECTS,
    CONTRACTS,
    CLIENTS,
    CONTACTS,
    SIDE_MENU_MAIN_GROUP_TITLE,
)
from res.utils import (
    PROJECT_EDITOR_SCREEN_ROUTE,
    CLIENT_EDITOR_SCREEN_ROUTE,
    CONTACT_EDITOR_SCREEN_ROUTE,
    CONTRACT_EDITOR_SCREEN_ROUTE,
)
from projects.views.projects_list import ProjectsListView
from clients.view.clients_list import ClientsListView
from contracts.view.contracts_list import ContractsListView
from contacts.view.contacts_destination_view import ContactsDestinationView
from typing import Callable
import typing
from core.abstractions import LocalCache

from flet import icons


class SideBarMenuItems(Enum):
    """Specifies the menu items mapped to a zero based index"""

    PROJECTS = 0
    CONTRACTS = 1
    CLIENTS = 2
    CONTACTS = 3


class SideBarMenuItemsHandler:
    """Manages home's side menu"""

    def __init__(
        self,
        localCacheHandler: LocalCache,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
    ):
        super().__init__()
        self.first_item_index = 0
        self.projectsView = ProjectsListView(
            localCacheHandler=localCacheHandler,
            onChangeRouteCallback=onChangeRouteCallback,
        )
        self.mainMenuTitle = SIDE_MENU_MAIN_GROUP_TITLE
        self.contactsView = ContactsDestinationView()
        self.clientsView = ClientsListView(
            localCacheHandler=localCacheHandler,
            onChangeRouteCallback=onChangeRouteCallback,
        )
        self.contractsView = ContractsListView(
            localCacheHandler=localCacheHandler,
            onChangeRouteCallback=onChangeRouteCallback,
        )

    def get_side_bar_menu_item_lbl(self, item: SideBarMenuItems) -> str:
        """returns a label given a menu item"""
        if item.value == SideBarMenuItems.PROJECTS.value:
            return PROJECTS
        elif item.value == SideBarMenuItems.CONTACTS.value:
            return CONTACTS
        elif item.value == SideBarMenuItems.CLIENTS.value:
            return CLIENTS
        else:
            return CONTRACTS

    def get_side_bar_menu_item_icon(self, item: SideBarMenuItems) -> str:
        """returns the un-selected-state-icon given a menu item"""
        if item.value == SideBarMenuItems.PROJECTS.value:
            return icons.WORK_OUTLINE
        elif item.value == SideBarMenuItems.CLIENTS.value:
            return icons.CONTACTS_OUTLINED
        elif item.value == SideBarMenuItems.CONTACTS.value:
            return icons.CONTACT_MAIL_OUTLINED
        else:
            return icons.HANDSHAKE_OUTLINED

    def get_side_bar_menu_item_selected_icon(self, item: SideBarMenuItems) -> str:
        """returns the selected-state-icon given a menu item"""
        if item.value == SideBarMenuItems.PROJECTS.value:
            return icons.WORK_ROUNDED
        elif item.value == SideBarMenuItems.CLIENTS.value:
            return icons.CONTACTS_ROUNDED
        elif item.value == SideBarMenuItems.CONTACTS.value:
            return icons.CONTACT_MAIL_ROUNDED
        else:
            return icons.HANDSHAKE_ROUNDED

    def get_side_bar_menu_item_from_index(self, index: int) -> SideBarMenuItems:
        """Given an integer index, returns the corresponding side menu item"""
        if index == SideBarMenuItems.PROJECTS.value:
            return SideBarMenuItems.PROJECTS
        elif index == SideBarMenuItems.CLIENTS.value:
            return SideBarMenuItems.CLIENTS
        elif index == SideBarMenuItems.CONTACTS.value:
            return SideBarMenuItems.CONTACTS
        else:
            return SideBarMenuItems.CONTRACTS

    def get_destination_view_for_item(self, menuItem):
        """Given a sidemenu item, returns the corresponding view"""
        if menuItem.value == SideBarMenuItems.PROJECTS.value:
            return self.projectsView
        elif menuItem.value == SideBarMenuItems.CLIENTS.value:
            return self.clientsView
        elif menuItem.value == SideBarMenuItems.CONTACTS.value:
            return self.contactsView
        else:
            return self.contractsView

    def get_new_item_route(self, menuItem: SideBarMenuItems):
        """Given a menu item, returns route for the view responsible for creating the corresponding item

        e.g. item project ---> return route for New Project screen
        """
        if menuItem.value == SideBarMenuItems.PROJECTS.value:
            return PROJECT_EDITOR_SCREEN_ROUTE
        elif menuItem.value == SideBarMenuItems.CLIENTS.value:
            return CLIENT_EDITOR_SCREEN_ROUTE
        elif menuItem.value == SideBarMenuItems.CONTACTS.value:
            return CONTACT_EDITOR_SCREEN_ROUTE
        else:
            return CONTRACT_EDITOR_SCREEN_ROUTE
