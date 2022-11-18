import typing
from typing import Callable
from flet import ProgressRing, Column, Container, ResponsiveRow, UserControl, padding

from authentication.intent.auth_intent_impl import AuthIntentImpl
from core.abstractions.local_cache import LocalCache
from core.abstractions.view import TuttleView
from core.ui.components.images.app_logo import labelledLogo
from core.ui.components.spacers import stdSpace
from core.ui.components.text import headlines
from core.ui.utils.flet_constants import CENTER_ALIGNMENT
from res import spacing, strings
from res.utils import HOME_SCREEN_ROUTE
from authentication.abstractions.auth_view import AuthView
from .components.login_form import LoginForm
from .components.splash_section import splashSection


class SplashScreen(AuthView):
    def __init__(
        self,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        localCacheHandler: LocalCache,
    ):
        super().__init__(
            changeRouteCallback=changeRouteCallback, localCacheHandler=localCacheHandler
        )

    def on_log_in_clicked(
        self, title: str, name: str, email: str, phone: str, address: str
    ):
        return self.intentHandler.create_user(
            title=title, name=name, email=email, phone=phone, address=address
        )

    def on_logged_in(
        self,
        data: typing.Optional[any] = None,
    ):
        self.changeRoute(HOME_SCREEN_ROUTE, data)

    def check_auth_status(self):
        """checks if user is already created

        if created, re routes to home
        else shows login form
        """
        isCreated = self.intentHandler.is_user_created()
        if isCreated:
            self.on_logged_in()
        else:
            self.show_login_form()

    def show_login_form(self):
        form = LoginForm(
            onLoggedIn=self.on_logged_in,
            onLogInClicked=self.on_log_in_clicked,
        )
        self.formContainer.controls.remove(self.progressBar)
        self.formContainer.controls.append(form)
        self.update()

    def did_mount(self):
        #TODO self.check_auth_status()
        self.on_logged_in()

    def build(self):
        """Called when page is built"""
        self.progressBar = ProgressRing(width=16, height=16, stroke_width=2)
        self.formContainer = Column(
            controls=[
                labelledLogo,
                headlines.get_headline_with_subtitle(
                    strings.WELCOME_TITLE, strings.WELCOME_SUBTITLE
                ),
                self.progressBar,
                stdSpace,
            ]
        )
        page_view = ResponsiveRow(
            spacing=0,
            run_spacing=0,
            alignment=CENTER_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[
                splashSection,
                Container(
                    col={"xs": 12, "md": 6},
                    padding=padding.all(spacing.SPACE_XL),
                    content=self.formContainer,
                ),
            ],
        )
        page_view.padding = spacing.SPACE_STD
        return page_view
