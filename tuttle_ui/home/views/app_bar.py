from typing import Callable

from flet import AppBar, IconButton, Row, icons

from core.views.flet_constants import CENTER_ALIGNMENT
from core.views.images import get_app_logo
from res.colors import BLACK_COLOR, PRIMARY_COLOR


def get_app_bar(onClickNew: Callable, onClickNotifications: Callable):
    return AppBar(
        bgcolor=BLACK_COLOR,
        elevation=12,
        title=Row(
            width=50,
            alignment=CENTER_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[
                get_app_logo(width=10),
            ],
        ),
        center_title=False,
        actions=[
            IconButton(
                icons.ADD_CIRCLE_OUTLINE_OUTLINED,
                icon_color=PRIMARY_COLOR,
                icon_size=20,
                on_click=onClickNew,
            ),
            IconButton(
                icons.NOTIFICATIONS,
                icon_color=PRIMARY_COLOR,
                icon_size=20,
                on_click=onClickNotifications,
            ),
        ],
    )
