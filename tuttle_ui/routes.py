import re
from typing import Callable

from flet import TemplateRoute, View

from user.view.splash_screen import SplashScreen
from user.view.profile_screen import ProfileScreen
from home.home_screen import HomeScreen
from core.views.error_404_view import Error404Screen
from contracts.view.contract_details import ContractDetailsScreen
from core.abstractions import TuttleView
from core.abstractions import LocalCache
from core.views.flet_constants import AUTO_SCROLL
from res.utils import (
    HOME_SCREEN_ROUTE,
    SPLASH_SCREEN_ROUTE,
    PROJECT_EDITOR_SCREEN_ROUTE,
    PROJECT_DETAILS_SCREEN_ROUTE,
    CONTRACT_DETAILS_SCREEN_ROUTE,
    CONTRACT_EDITOR_SCREEN_ROUTE,
    PROFILE_SCREEN_ROUTE,
    PREFERENCES_SCREEN_ROUTE,
)
from projects.views.project_details import ProjectDetailsScreen
from projects.views.project_editor import ProjectEditorScreen
from dataclasses import dataclass
from contracts.view.contract_editor import ContractEditorScreen
from preferences.view.preferences_screen import PreferencesScreen


@dataclass
class RouteView:
    """A utility class that defines a route view"""

    view: View
    keepBackStack: bool


class TuttleRoutes:
    """Utility class for parsing of routes to destination views

    onChangeRouteCallback - used by views for routing
    localCacheHandler - used by views for cache access
    """

    def __init__(
        self,
        onChangeRouteCallback: Callable[[str, any], None],
        localCacheHandler: LocalCache,
        dialogController: Callable,
        onNavigateBack: Callable,
        showSnackCallback: Callable,
        onThemeChangedCallback: Callable,
    ):
        self.onChangeRouteCallback = onChangeRouteCallback
        self.localCacheHandler = localCacheHandler
        self.dialogController = dialogController
        self.onNavigateBack = onNavigateBack
        self.showSnackCallback = showSnackCallback
        self.onThemeChangedCallback = onThemeChangedCallback

    def get_page_route_view(
        self,
        routeName: str,
        hasAppBar: bool,
        hasFloatingAction: bool,
        screen: TuttleView,
        scrollType: str = AUTO_SCROLL,
    ) -> RouteView:
        """Constructs the view with a given route

        checks if view has an app bar or floating action button
        then appends to view if available
        """

        view = View(
            padding=0,
            spacing=0,
            route=routeName,
            scroll=scrollType,
            controls=[screen],
            vertical_alignment=screen.verticalAlignmentInParent,
            horizontal_alignment=screen.horizontalAlignmentInParent,
        )

        if hasAppBar:
            view.appbar = screen.get_app_bar_if_any()
        if hasFloatingAction:
            view.floating_action_button = screen.get_floating_action_btn_if_any()

        return RouteView(view=view, keepBackStack=screen.keepBackStack)

    def parse_route(self, pageRoute: str):
        """parses a given route path and returns it's view"""

        routePath = TemplateRoute(pageRoute)

        if routePath.match(SPLASH_SCREEN_ROUTE):
            splashScreen = SplashScreen(
                changeRouteCallback=self.onChangeRouteCallback,
                localCacheHandler=self.localCacheHandler,
            )
            return self.get_page_route_view(
                SPLASH_SCREEN_ROUTE,
                hasAppBar=splashScreen.hasAppBar,
                hasFloatingAction=splashScreen.hasFloatingActionBtn,
                screen=splashScreen,
            )
        elif routePath.match(HOME_SCREEN_ROUTE) or routePath.match(
            f"{HOME_SCREEN_ROUTE}/:userId"
        ):
            homeScreen = HomeScreen(
                changeRouteCallback=self.onChangeRouteCallback,
                localCacheHandler=self.localCacheHandler,
                dialogController=self.dialogController,
                showSnackCallback=self.showSnackCallback,
            )
            return self.get_page_route_view(
                HOME_SCREEN_ROUTE,
                hasAppBar=homeScreen.hasAppBar,
                hasFloatingAction=homeScreen.hasFloatingActionBtn,
                screen=homeScreen,
            )
        elif routePath.match(PROJECT_EDITOR_SCREEN_ROUTE) or routePath.match(
            f"{PROJECT_EDITOR_SCREEN_ROUTE}/:projectId"
        ):
            projectId = None
            if hasattr(routePath, "projectId"):
                projectId = routePath.projectId
            projectEditorScreen = ProjectEditorScreen(
                changeRouteCallback=self.onChangeRouteCallback,
                localCacheHandler=self.localCacheHandler,
                onNavigateBack=self.onNavigateBack,
                pageDialogController=self.dialogController,
                showSnackCallback=self.showSnackCallback,
                projectId=projectId,
            )
            return self.get_page_route_view(
                PROJECT_EDITOR_SCREEN_ROUTE,
                hasAppBar=projectEditorScreen.hasAppBar,
                hasFloatingAction=projectEditorScreen.hasFloatingActionBtn,
                screen=projectEditorScreen,
            )

        elif routePath.match(f"{PROJECT_DETAILS_SCREEN_ROUTE}/:projectId"):
            projectDetailsScreen = ProjectDetailsScreen(
                changeRouteCallback=self.onChangeRouteCallback,
                localCacheHandler=self.localCacheHandler,
                onNavigateBack=self.onNavigateBack,
                pageDialogController=self.dialogController,
                showSnackCallback=self.showSnackCallback,
                projectId=routePath.projectId,
            )
            return self.get_page_route_view(
                PROJECT_DETAILS_SCREEN_ROUTE,
                hasAppBar=projectDetailsScreen.hasAppBar,
                hasFloatingAction=projectDetailsScreen.hasFloatingActionBtn,
                screen=projectDetailsScreen,
            )
        elif routePath.match(f"{CONTRACT_DETAILS_SCREEN_ROUTE}/:contractId"):
            contractDetailsScreen = ContractDetailsScreen(
                changeRouteCallback=self.onChangeRouteCallback,
                localCacheHandler=self.localCacheHandler,
                onNavigateBack=self.onNavigateBack,
                pageDialogController=self.dialogController,
                showSnackCallback=self.showSnackCallback,
                contractId=routePath.contractId,
            )
            return self.get_page_route_view(
                PROJECT_DETAILS_SCREEN_ROUTE,
                hasAppBar=contractDetailsScreen.hasAppBar,
                hasFloatingAction=contractDetailsScreen.hasFloatingActionBtn,
                screen=contractDetailsScreen,
            )
        elif routePath.match(CONTRACT_EDITOR_SCREEN_ROUTE):
            contractEditorScreen = ContractEditorScreen(
                changeRouteCallback=self.onChangeRouteCallback,
                localCacheHandler=self.localCacheHandler,
                onNavigateBack=self.onNavigateBack,
                pageDialogController=self.dialogController,
                showSnackCallback=self.showSnackCallback,
            )
            return self.get_page_route_view(
                CONTRACT_EDITOR_SCREEN_ROUTE,
                hasAppBar=contractEditorScreen.hasAppBar,
                hasFloatingAction=contractEditorScreen.hasFloatingActionBtn,
                screen=contractEditorScreen,
            )
        elif routePath.match(PROFILE_SCREEN_ROUTE):
            profileScreen = ProfileScreen(
                changeRouteCallback=self.onChangeRouteCallback,
                localCacheHandler=self.localCacheHandler,
                dialogController=self.dialogController,
                showSnackCallback=self.showSnackCallback,
                onNavigateBack=self.onNavigateBack,
            )
            return self.get_page_route_view(
                PROFILE_SCREEN_ROUTE,
                hasAppBar=profileScreen.hasAppBar,
                hasFloatingAction=profileScreen.hasFloatingActionBtn,
                screen=profileScreen,
            )
        elif routePath.match(PREFERENCES_SCREEN_ROUTE):
            preferencesScreen = PreferencesScreen(
                localCacheHandler=self.localCacheHandler,
                onNavigateBack=self.onNavigateBack,
                showSnackCallback=self.showSnackCallback,
                onThemeChangedCallback=self.onThemeChangedCallback,
            )
            return self.get_page_route_view(
                PREFERENCES_SCREEN_ROUTE,
                hasAppBar=preferencesScreen.hasAppBar,
                hasFloatingAction=preferencesScreen.hasFloatingActionBtn,
                screen=preferencesScreen,
            )
        else:
            err404Screen = Error404Screen(
                changeRouteCallback=self.onChangeRouteCallback
            )
            return self.get_page_route_view(
                "/404",
                hasAppBar=err404Screen.hasAppBar,
                hasFloatingAction=err404Screen.hasFloatingActionBtn,
                screen=err404Screen,
            )
