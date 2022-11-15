from typing import Callable

import flet
from flet import Column, Container, ResponsiveRow, UserControl, padding

from authentication.intent.auth_intent import AuthIntent
from core.abstractions.view import TuttleScreen
from core.ui.components.images import images
from core.ui.components.images.app_logo import labelledLogo
from core.ui.components.spacers import mdSpace
from core.ui.components.text import headlines
from core.ui.utils.flet_constants import (ALIGN_CENTER, CENTER_ALIGNMENT,
                                          START_ALIGNMENT)
from res import spacing, strings
from res.fonts import headline3Size, headline4Size
from res.image_paths import splashImgPath
from res.utils import HOME_SCREEN_ROUTE

from .components.login_form import LoginForm


class SplashScreen(TuttleScreen, UserControl):
    """Initial Screen Displayed
    
    If the user is authenticated,
    re-route them to home Screen
    else display a login form and a splash section
    """
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

    def on_log_in_clicked(self, title :str, name : str, email : str, phone : str, address : str):
        return self.intent.attempt_login(title=title, name=name,email=email,phone=phone, address=address)

    def on_logged_in(self, data : any):
        self.routeToCallback(HOME_SCREEN_ROUTE, data)

    def get_login_form(self):
        """Displays the login form"""
        return Container(
                        col={"xs" : 12, "md": 6},
                        padding=padding.all(spacing.SPACE_XL),
                    content=Column(
                        controls=[
                            labelledLogo,
                            headlines.get_headline_with_subtitle(
                                strings.WELCOME_TITLE, 
                                strings.WELCOME_SUBTITLE
                            ),
                            mdSpace,
                            LoginForm(onLoggedIn = self.on_logged_in, onLogInClicked=self.on_log_in_clicked)
                            ]
                    ))


    def get_about_tuttle_view(self):
        """Displays quick info about Tuttle app"""
        return Container(
                        col={"xs" : 12, "md": 6},
                        padding=padding.all(spacing.SPACE_XS),
                        content=Column(
                            alignment= START_ALIGNMENT,
                            horizontal_alignment=CENTER_ALIGNMENT,
                            expand=True,
                            controls=[
                                mdSpace,
                                images.get_image(
                                    splashImgPath,
                                    strings.SPLASH_IMG_SEMANTIC_LBL,
                                    width=300
                                ),
                                headlines.get_headline_with_subtitle(strings.APP_NAME, strings.APP_DESCRIPTION, alignmentInContainer=CENTER_ALIGNMENT, txtAlignment=ALIGN_CENTER, titleSize=headline3Size, subtitleSize=headline4Size),
                            ]
                        )
                        )

    def build(self):
        """Called when page is built"""
        page_view = ResponsiveRow(
                spacing = 0,
                run_spacing = 0,
                alignment = CENTER_ALIGNMENT,
                vertical_alignment = CENTER_ALIGNMENT,
                controls = [
                    self.get_about_tuttle_view(),
                    self.get_login_form()
                    ]
            )
        page_view.padding = spacing.SPACE_STD
        return page_view

