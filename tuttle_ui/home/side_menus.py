from dataclasses import dataclass

from res.strings import (
    INVOICE,
    PROJECTS,
    CONTRACTS,
    CLIENTS,
    CONTACTS,
    MAIN_MENU_GROUP_TITLE,
    SECONDARY_MENU_GROUP_TITLE,
)
from res.utils import (
    PROJECT_CREATOR_SCREEN_ROUTE,
    ADD_CLIENT_INTENT,
    ADD_CONTACT_INTENT,
    CONTRACT_CREATOR_SCREEN_ROUTE,
)
from core.abstractions import TuttleView
from typing import Optional
from clients.views.list_view import ClientsListView
from contacts.views.list_view import ContactsListView
from contracts.views.list_view import ContractsListView
from projects.views.list_view import ProjectsListView
from flet import icons, Container


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
        self.items = [
            MenuItems(
                0,
                PROJECTS,
                icons.WORK_OUTLINE,
                icons.WORK_ROUNDED,
                self.projects_view,
                on_new_screen_route=PROJECT_CREATOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
            MenuItems(
                1,
                CONTACTS,
                icons.CONTACT_MAIL_OUTLINED,
                icons.CONTACT_MAIL_ROUNDED,
                self.contacts_view,
                on_new_screen_route=None,
                on_new_intent=ADD_CONTACT_INTENT,
            ),
            MenuItems(
                2,
                CLIENTS,
                icons.CONTACTS_OUTLINED,
                icons.CONTACTS_ROUNDED,
                self.clients_view,
                on_new_screen_route=None,
                on_new_intent=ADD_CLIENT_INTENT,
            ),
            MenuItems(
                3,
                CONTRACTS,
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
        self.menu_title = SECONDARY_MENU_GROUP_TITLE
        self.items = [
            MenuItems(
                0,
                INVOICE,
                icons.ATTACH_MONEY_OUTLINED,
                icons.ATTACH_MONEY_ROUNDED,
                Container(),
                "/404",
            )
        ]
