import flet
from flet import (
    UserControl,  Image, 
    Text, Row, Column, Icon, icons, Container,
)
from res import fonts, strings, colors
from core.abstractions.tuttle_screen import TuttleScreen
from core.ui.components.images import app_logo
from core.ui.components.text import headlines

logoLabelled = Row(
                    vertical_alignment="center",
                    controls=[
                    app_logo.getAppLogo(),
                    headlines.getHeadlineTxt(
                        strings.appName, 
                        size=fonts.headline3Size,
                        color=colors.BLACK_COLOR
                        ),
                    ]
                  )