from typing import Callable

from flet import Container, Text, padding, IconButton, Row, icons, alignment

from core.views.flet_constants import SPACE_BETWEEN_ALIGNMENT, CENTER_ALIGNMENT
from core.views.images import get_app_logo
from res.colors import BLACK_COLOR, PRIMARY_COLOR
from res.spacing import SPACE_MD
from res.strings import APP_NAME
from res.fonts import HEADLINE_4_SIZE, HEADLINE_FONT
from core.views.texts import get_std_txt_field


def get_action_bar(onClickNew: Callable, onClickNotifications: Callable):
    return Container(
        bgcolor=BLACK_COLOR,
        alignment=alignment.center,
        height=56,
        padding=padding.symmetric(horizontal=SPACE_MD),
        content=Row(
            alignment=SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[
                Row(
                    controls=[
                        get_app_logo(width=10),
                        Text(APP_NAME, size=HEADLINE_4_SIZE, font_family=HEADLINE_FONT),
                    ],
                    alignment=CENTER_ALIGNMENT,
                    vertical_alignment=CENTER_ALIGNMENT,
                ),
                Row(
                    controls=[
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
                    ]
                ),
            ],
        ),
    )
