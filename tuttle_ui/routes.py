import re
from typing import Callable

from flet import TemplateRoute, View

from authentication.view.splash_screen import SplashScreen
from home.view.home_screen import HomeScreen
from core.ui.default_views.err404Screen import Error404Screen

from core.abstractions.view import TuttleScreen
from core.ui.utils.flet_constants import AUTO_SCROLL
from res.utils import HOME_SCREEN_ROUTE, SPLASH_SCREEN_ROUTE


class TuttleRoutes():
    """Utility class for parsing of routes to destination views"""
    
    def __init__(self, onChangeRouteCallback : Callable[[str, any], None]):
        # to be passed to views for routing to another destination
        self.onChangeRouteCallback  = onChangeRouteCallback

    def get_page_route_view(self, routeName : str, hasAppBar : bool, hasFloatingAction : bool, screen : TuttleScreen, scrollType : str = AUTO_SCROLL):
        """Constructs the view with a given route
        
        checks if view has an app bar or floating action button
        then appends to view if available
        """
        view = View(padding=0, spacing=0, route=routeName, scroll=scrollType, controls=[screen], bgcolor=screen.bg_color)
        
        if hasAppBar:
            view.appbar = screen.get_app_bar_if_any()
        if hasFloatingAction:
            view.floating_action_button = screen.get_floating_action_btn_if_any()
        return view

    def parse_route(self, pageRoute : str):
        """parses a given route path and returns it's view"""
        routePath = TemplateRoute(pageRoute)
        print(routePath)
        print(pageRoute)
        print("hihihi")
        if routePath.match(SPLASH_SCREEN_ROUTE):
            splashScreen = SplashScreen(onChangeRouteCallback=self.onChangeRouteCallback)
            return self.get_page_route_view(
                SPLASH_SCREEN_ROUTE, 
                hasAppBar=splashScreen.has_app_bar,
                hasFloatingAction=splashScreen.has_floating_action_btn,
                screen=splashScreen
            )
        elif routePath.match(HOME_SCREEN_ROUTE):
            homeScreen = HomeScreen(onChangeRouteCallback=self.onChangeRouteCallback)
            return self.get_page_route_view(
                HOME_SCREEN_ROUTE, 
                hasAppBar=homeScreen.has_app_bar,
                hasFloatingAction=homeScreen.has_floating_action_btn,
                screen=homeScreen
            )

        else:
            err404Screen = Error404Screen(onChangeRouteCallback=self.onChangeRouteCallback)
            return self.get_page_route_view(
                '/404', 
                hasAppBar=err404Screen.has_app_bar,
                hasFloatingAction=err404Screen.has_floating_action_btn,
                screen=err404Screen
            )
