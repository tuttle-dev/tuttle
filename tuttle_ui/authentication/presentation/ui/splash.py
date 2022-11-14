import flet
from flet import (Column, Container, Icon, Image, ResponsiveRow, Row, Text,
                  UserControl, icons, padding)

from core.abstractions.tuttle_screen import TuttleScreen
from core.ui.components.text import headlines
from res import colors, fonts, spacing, strings

from .components.logo_labelled import logoLabelled
from .components.login_form import LoginForm
from core.ui.components.spacers import mdSpace

class SplashScreen(TuttleScreen, UserControl):
    def __init__(self):
        super().__init__(hasFloatingActionBtn=False, hasAppBar=False)

    def getFloatingActionBtnIfAny(self):
        return None

    def getAppBarIfAny(self):
        return None

    # displays login form on the left side 
    def authView(self):
        return Container(
                        col={"md": 6},
                        padding=padding.all(40),
                    content=Column(
                        controls=[
                            logoLabelled,
                            headlines.getHeadlineWithSubtitle(
                                strings.welcomeTitle, 
                                strings.welcomeSubTitle
                            ),
                            mdSpace,
                            LoginForm()
                            ]
                    ))


    def splashView(self):
        return Container(
                        col={"md": 6},
                        bgcolor="blue",
                        content=Text("TODO")
                        )

    def build(self):
        page_view = Container( 
            padding=0,
            margin=0,
            content = ResponsiveRow(
                spacing = spacing.SPACE_MD,
                run_spacing = spacing.SPACE_MD,
                alignment = "spaceBetween",
                vertical_alignment = "start",
                controls = [
                    self.authView(),
                    self.splashView() 
                    ]
            ))
        page_view.padding = spacing.SPACE_STD
        return page_view

