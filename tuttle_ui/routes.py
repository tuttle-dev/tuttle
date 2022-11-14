import re
import repath
import flet
from flet import TemplateRoute, View
from core.abstractions.tuttle_screen import TuttleScreen
from authentication.presentation.ui.splash import SplashScreen

#uses python repath
# https://github.com/nickcoutsos/python-repath

class TuttleRoutes():
    def __init__(self):
        self.splashScreenRoute = '/'
        self.registrationRoute = '/register'

    def pageRouteView(self, routeName, hasAppBar, hasFloatingAction, screen : TuttleScreen):
        view = View(padding=0, spacing=0, route=routeName, controls=[screen])
        if hasAppBar:
            view.appbar = screen.getAppBarIfAny()
        if hasFloatingAction:
            view.floating_action_button = screen.getFloatingActionBtnIfAny()
        return view

    def parseRoute(self, pageRoute):
        #parses a given route and returns it's view
        routePath = TemplateRoute(pageRoute)
        if routePath.match(self.splashScreenRoute):
            splashScreen = SplashScreen()
            return self.pageRouteView(
                self.splashScreenRoute, 
                hasAppBar=splashScreen.hasAppBar,
                hasFloatingAction=splashScreen.hasFloatingActionBtn,
                screen=splashScreen
            )
        else:
            print("unknown path")
