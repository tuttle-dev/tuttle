from core.abstractions import TuttleView, ClientStorage
from typing import Callable
from flet import Container, UserControl, UserControl
import typing
from typing import Callable

from flet import Column, Container, ResponsiveRow, UserControl, padding

from ..auth_intent_impl import AuthIntentImpl
from core.constants_and_enums import CENTER_ALIGNMENT
from core.views import (
    horizontalProgressBar,
    get_labelled_logo,
    stdSpace,
    get_headline_with_subtitle,
)
from res.dimens import SPACE_XL, SPACE_XS
from res.strings import WELCOME_TITLE, WELCOME_SUBTITLE
from res.utils import HOME_SCREEN_ROUTE

from .login_form import LoginForm
from .splash_view import SplashView


class SplashScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route: Callable,
        show_snack: Callable,
        dialog_controller: Callable,
        local_storage: ClientStorage,
    ):
        super().__init__(
            navigate_to_route,
            show_snack,
            dialog_controller,
            keep_back_stack=False,
        )
        self.intent_handler = AuthIntentImpl(local_storage=local_storage)

    def on_save_user(
        self,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        street_num: str,
        postal_code: str,
        city: str,
        country: str,
    ):
        return self.intent_handler.create_user(
            title=title,
            name=name,
            email=email,
            phone=phone,
            street=street,
            street_num=street_num,
            postal_code=postal_code,
            city=city,
            country=country,
        )

    def on_logged_in(self):
        self.navigate_to_route(HOME_SCREEN_ROUTE)

    def check_auth_status(self):
        """checks if user is already created

        if created, re routes to home
        else shows login form
        """
        result = self.intent_handler.get_user_test_login()
        if result.was_intent_successful:
            if result.data is not None:
                self.on_logged_in()
            else:
                self.show_login_form()
        else:
            self.show_snack(result.error_msg)

    def show_login_form(self):
        form = LoginForm(
            on_logged_in=self.on_logged_in,
            on_save_user=self.on_save_user,
        )
        self.form_container.controls.remove(self.loading_indicator)
        self.form_container.controls.append(form)
        self.update()

    def did_mount(self):
        try:
            self.check_auth_status()
            # self.on_logged_in()
        except Exception as e:
            # log
            print(f"exception raised @splash_screen.did_mount {e}")

    def build(self):
        """Called when page is built"""
        self.loading_indicator = horizontalProgressBar
        self.form_container = Column(
            controls=[
                get_labelled_logo(),
                get_headline_with_subtitle(WELCOME_TITLE, WELCOME_SUBTITLE),
                self.loading_indicator,
                stdSpace,
            ]
        )
        page_view = ResponsiveRow(
            spacing=0,
            run_spacing=0,
            alignment=CENTER_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[
                Container(
                    col={"xs": 12, "sm": 5},
                    padding=padding.all(SPACE_XS),
                    content=SplashView(),
                ),
                Container(
                    col={"xs": 12, "sm": 7},
                    padding=padding.all(SPACE_XL),
                    content=self.form_container,
                ),
            ],
        )
        return page_view
