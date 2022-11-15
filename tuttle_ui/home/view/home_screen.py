from typing import Callable

from flet import Text, ResponsiveRow, UserControl
from authentication.intent.auth_intent import AuthIntent
from core.abstractions.view import TuttleScreen
from core.ui.utils.flet_constants import CENTER_ALIGNMENT
from res import spacing


class HomeScreen(TuttleScreen, UserControl):
    def __init__(self, onChangeRouteCallback: Callable[[str, any], None]):
        super().__init__(hasFloatingActionBtn=False, hasAppBar=False,)
        self.set_intent_handler(intentHandler=AuthIntent())
        self.set_route_to_callback(onChangeRouteCallback)

    def set_intent_handler(self, intentHandler: AuthIntent):
         self.intent = intentHandler

    def set_route_to_callback(self, onChangeRouteCallback: Callable[[str], None]):
        self.routeToCallback = onChangeRouteCallback

    def get_floating_action_btn_if_any(self):
        return None

    def get_app_bar_if_any(self):
        return None

    def build(self):
        """Called when page is built"""
        page_view = ResponsiveRow(
                spacing = 0,
                run_spacing = 0,
                alignment = CENTER_ALIGNMENT,
                vertical_alignment = CENTER_ALIGNMENT,
                controls = [
                     Text("Home")
                    ]
            )
        page_view.padding = spacing.SPACE_STD
        return page_view

