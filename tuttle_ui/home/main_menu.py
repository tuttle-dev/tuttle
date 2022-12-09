from enum import Enum
from res.strings import (
    PROJECTS,
    CONTRACTS,
    CLIENTS,
    CONTACTS,
    MAIN_MENU_GROUP_TITLE,
)
from res.utils import (
    PROJECT_CREATOR_SCREEN_ROUTE,
    ADD_CLIENT_INTENT,
    ADD_CONTACT_INTENT,
    CONTRACT_CREATOR_SCREEN_ROUTE,
)
from core.abstractions import TuttleView, ClientStorage
from typing import Callable
from clients.views.list_view import ClientsListView
from contacts.views.list_view import ContactsListView
from contracts.views.list_view import ContractsListView
from projects.views.list_view import ProjectsListView
from flet import icons, Container


class MainMenuItems(Enum):
    """Specifies the main menu items mapped to a zero based index"""

    PROJECTS = 0
    CONTRACTS = 1
    CLIENTS = 2
    CONTACTS = 3


class MainMenuItemsHandler:
    """Manages home's main menu"""

    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        local_storage,
    ):
        super().__init__()
        self.first_item_index = 0
        self.menu_title = MAIN_MENU_GROUP_TITLE

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

    def get_menu_item_lbl(self, item: MainMenuItems) -> str:
        """returns a label given a menu item"""
        if item.value == MainMenuItems.PROJECTS.value:
            return PROJECTS
        elif item.value == MainMenuItems.CONTACTS.value:
            return CONTACTS
        elif item.value == MainMenuItems.CLIENTS.value:
            return CLIENTS
        else:
            return CONTRACTS

    def get_menu_item_icon(self, item: MainMenuItems) -> str:
        """returns the un-selected-state-icon given a menu item"""
        if item.value == MainMenuItems.PROJECTS.value:
            return icons.WORK_OUTLINE
        elif item.value == MainMenuItems.CLIENTS.value:
            return icons.CONTACTS_OUTLINED
        elif item.value == MainMenuItems.CONTACTS.value:
            return icons.CONTACT_MAIL_OUTLINED
        else:
            return icons.HANDSHAKE_OUTLINED

    def get_menu_item_selected_icon(self, item: MainMenuItems) -> str:
        """returns the selected-state-icon given a menu item"""
        if item.value == MainMenuItems.PROJECTS.value:
            return icons.WORK_ROUNDED
        elif item.value == MainMenuItems.CLIENTS.value:
            return icons.CONTACTS_ROUNDED
        elif item.value == MainMenuItems.CONTACTS.value:
            return icons.CONTACT_MAIL_ROUNDED
        else:
            return icons.HANDSHAKE_ROUNDED

    def get_menu_item_from_index(self, index: int) -> MainMenuItems:
        """Given an integer index, returns the corresponding side menu item"""
        if index == MainMenuItems.PROJECTS.value:
            return MainMenuItems.PROJECTS
        elif index == MainMenuItems.CLIENTS.value:
            return MainMenuItems.CLIENTS
        elif index == MainMenuItems.CONTACTS.value:
            return MainMenuItems.CONTACTS
        else:
            return MainMenuItems.CONTRACTS

    def get_menu_destination_view_for_item(
        self, menu_item: MainMenuItems
    ) -> TuttleView:
        """Given a sidemenu item, returns the corresponding view"""
        if menu_item.value == MainMenuItems.PROJECTS.value:
            return self.projects_view
        elif menu_item.value == MainMenuItems.CLIENTS.value:
            return self.clients_view
        elif menu_item.value == MainMenuItems.CONTACTS.value:
            return self.contacts_view
        else:
            return self.contracts_view

    def get_create_route_or_intent(self, menu_item: MainMenuItems):
        """Given a menu item, returns route for the view responsible for creating the corresponding item

        e.g. item project ---> return route for New Project screen
        """
        if menu_item.value == MainMenuItems.PROJECTS.value:
            return PROJECT_CREATOR_SCREEN_ROUTE
        elif menu_item.value == MainMenuItems.CLIENTS.value:
            return ADD_CLIENT_INTENT
        elif menu_item.value == MainMenuItems.CONTACTS.value:
            return ADD_CONTACT_INTENT
        else:
            return CONTRACT_CREATOR_SCREEN_ROUTE
