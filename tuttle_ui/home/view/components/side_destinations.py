from enum import Enum
from res.strings import PROJECTS, CONTRACTS, CLIENTS, CONTACTS
from projects.view.projects_destination_view import ProjectsDestinationView
from clients.view.clients_destination_view import ClientsDestinationView
from contracts.view.contracts_destination_view import ContractsDestinationView
from contacts.view.contacts_destination_view import ContactsDestinationView

from flet import icons


class SideBarMenuItems(Enum):
    """Specifies the menu items mapped to a zero based index"""

    PROJECTS = 0
    CONTRACTS = 1
    CLIENTS = 2
    CONTACTS = 3


class SideBarMenuItemsHandler:
    """Manages home's side menu"""

    def __init__(self):
        super().__init__()
        self.first_item_index = 0
        self.projectsView = ProjectsDestinationView()
        self.contactsView = ContactsDestinationView()
        self.clientsView = ClientsDestinationView()
        self.contractsView = ContractsDestinationView()

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
