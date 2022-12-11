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
from time_tracking.view import TimeTrackingView
from flet import icons, Icon, Container


@dataclass
class MenuItem:
    """defines a menu item"""

    # index: int
    label: str
    icon: Icon
    selected_icon: Icon
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
            # a menu item for a dashboard
            MenuItem(
                # index=0,
                label="Dashboard",
                icon=icons.SPEED_OUTLINED,
                selected_icon=icons.SPEED_ROUNDED,
                destination=Container(),
                on_new_screen_route="/404",
            ),
            MenuItem(
                # index=0,
                label=PROJECTS,
                icon=icons.WORK_OUTLINE,
                selected_icon=icons.WORK_ROUNDED,
                destination=self.projects_view,
                on_new_screen_route=PROJECT_CREATOR_SCREEN_ROUTE,
                on_new_intent=None,
            ),
            MenuItem(
                # index=1,
                label=CONTACTS,
                icon=icons.CONTACT_MAIL_OUTLINED,
                selected_icon=icons.CONTACT_MAIL_ROUNDED,
                destination=self.contacts_view,
                on_new_screen_route=None,
                on_new_intent=ADD_CONTACT_INTENT,
            ),
            MenuItem(
                # index=2,
                label=CLIENTS,
                icon=icons.CONTACTS_OUTLINED,
                selected_icon=icons.CONTACTS_ROUNDED,
                destination=self.clients_view,
                on_new_screen_route=None,
                on_new_intent=ADD_CLIENT_INTENT,
            ),
            MenuItem(
                # index=3,
                label=CONTRACTS,
                icon=icons.HANDSHAKE_OUTLINED,
                selected_icon=icons.HANDSHAKE_ROUNDED,
                destination=self.contracts_view,
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

        self.time_tracking_view = TimeTrackingView(
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            navigate_to_route=navigate_to_route,
            local_storage=local_storage,
        )

        self.items = [
            # a menu item for time tracking
            MenuItem(
                # index=0,
                label="Time Tracking",
                icon=icons.TIMER_OUTLINED,
                selected_icon=icons.TIMER_ROUNDED,
                destination=self.time_tracking_view,
                on_new_screen_route="/404",
                on_new_intent=None,
            ),
            MenuItem(
                # index=1,
                label=INVOICE,
                icon=icons.ATTACH_MONEY_OUTLINED,
                selected_icon=icons.ATTACH_MONEY_ROUNDED,
                destination=Container(),
                on_new_screen_route="/404",
                on_new_intent=None,
            ),
        ]
