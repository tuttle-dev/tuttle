from core.constants_and_enums import (
    AUTO_SCROLL,
    NEVER_SHOW,
)
from core.models import RouteView
import re
from typing import Callable

from flet import TemplateRoute, View

from auth.views.splash_screen import SplashScreen
from home.home_screen import HomeScreen
from projects.views.view_project_screen import ViewProjectScreen
from projects.views.edit_project import EditProjectScreen
from projects.views.create_project import CreateProjectScreen
from contracts.views.view_contract_screen import ViewContractScreen
from contracts.views.contract_editor import ContractEditorScreen
from preferences.views.preferences_screen import PreferencesScreen
from error_views.page_not_found_screen import Error404Screen
from core.abstractions import TuttleView
from core.abstractions import ClientStorage
from contracts.views.create_contract import CreateContractScreen
from res.utils import (
    HOME_SCREEN_ROUTE,
    SPLASH_SCREEN_ROUTE,
    PROJECT_EDITOR_SCREEN_ROUTE,
    PROJECT_CREATOR_SCREEN_ROUTE,
    PROJECT_DETAILS_SCREEN_ROUTE,
    CONTRACT_DETAILS_SCREEN_ROUTE,
    CONTRACT_EDITOR_SCREEN_ROUTE,
    CONTRACT_CREATOR_SCREEN_ROUTE,
    PROFILE_SCREEN_ROUTE,
    PREFERENCES_SCREEN_ROUTE,
)
from auth.views.profile_screen import ProfileScreen


class TuttleRoutes:
    """Utility class for parsing of routes to destination views"""

    def __init__(
        self,
        on_change_route: Callable[[str, any], None],
        local_storage: ClientStorage,
        dialog_controller: Callable,
        on_navigate_back: Callable,
        show_snack: Callable,
        on_theme_changed: Callable,
    ):
        self.on_change_route = on_change_route
        self.local_storage = local_storage
        self.dialog_controller = dialog_controller
        self.on_navigate_back = on_navigate_back
        self.show_snack = show_snack
        self.on_theme_changed = on_theme_changed

    def get_page_route_view(
        self,
        routeName: str,
        view: TuttleView,
    ) -> RouteView:
        """Constructs the view with a given route"""

        view_container = View(
            padding=0,
            spacing=0,
            route=routeName,
            scroll=view.page_scroll_type,
            controls=[view],
            vertical_alignment=view.vertical_alignment_in_parent,
            horizontal_alignment=view.horizontal_alignment_in_parent,
        )

        return RouteView(
            view=view_container,
            on_window_resized=view.window_on_resized,
            keep_back_stack=view.keep_back_stack,
        )

    def parse_route(self, pageRoute: str):
        """parses a given route path and returns it's view"""

        routePath = TemplateRoute(pageRoute)
        screen = None
        if routePath.match(SPLASH_SCREEN_ROUTE):
            screen = SplashScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                local_storage=self.local_storage,
            )
        elif routePath.match(HOME_SCREEN_ROUTE):
            screen = HomeScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
            )
        elif routePath.match(PROFILE_SCREEN_ROUTE):
            screen = ProfileScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
            )
        elif routePath.match(PREFERENCES_SCREEN_ROUTE):
            screen = PreferencesScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
                on_theme_changed=self.on_theme_changed,
            )
        elif routePath.match(f"{PROJECT_DETAILS_SCREEN_ROUTE}/:projectId"):
            screen = ViewProjectScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
                project_id=routePath.projectId,
            )

        elif routePath.match(f"{CONTRACT_DETAILS_SCREEN_ROUTE}/:contractId"):
            screen = ViewContractScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
                contract_id=routePath.contractId,
            )

        elif routePath.match(CONTRACT_CREATOR_SCREEN_ROUTE):
            screen = CreateContractScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
            )
        elif routePath.match(f"{CONTRACT_EDITOR_SCREEN_ROUTE}/:contractId"):
            contractId = None
            if hasattr(routePath, "contractId"):
                contractId = routePath.contractId
            screen = ContractEditorScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
                contract_id=contractId,
            )

        elif routePath.match(PROJECT_CREATOR_SCREEN_ROUTE):
            screen = CreateProjectScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
            )
        elif routePath.match(PROJECT_EDITOR_SCREEN_ROUTE) or routePath.match(
            f"{PROJECT_EDITOR_SCREEN_ROUTE}/:projectId"
        ):
            projectId = None
            if hasattr(routePath, "projectId"):
                projectId = routePath.projectId
            screen = EditProjectScreen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
                local_storage=self.local_storage,
                project_id=projectId,
            )

        else:
            screen = Error404Screen(
                navigate_to_route=self.on_change_route,
                show_snack=self.show_snack,
                dialog_controller=self.dialog_controller,
                on_navigate_back=self.on_navigate_back,
            )

        return self.get_page_route_view(
            routePath.route,
            view=screen,
        )
