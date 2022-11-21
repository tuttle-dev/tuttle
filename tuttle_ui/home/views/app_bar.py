from typing import Callable

from flet import AppBar, IconButton, Row, icons

from core.views.images import get_app_logo
from core.views.flet_constants import CENTER_ALIGNMENT
from res import colors


def get_app_bar(on_click_notifications: Callable):
    return AppBar(
        bgcolor=colors.BLACK_COLOR,
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
                icons.NOTIFICATIONS,
                icon_color=colors.PRIMARY_COLOR,
                icon_size=20,
                on_click=on_click_notifications,
            ),
        ],
    )
