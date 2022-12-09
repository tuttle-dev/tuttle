from typing import Callable

from flet import (
    Container,
    Text,
    padding,
    IconButton,
    Row,
    icons,
    alignment,
    ElevatedButton,
)

from core.constants_and_enums import SPACE_BETWEEN_ALIGNMENT, CENTER_ALIGNMENT
from core.views import get_app_logo, get_std_txt_field
from res.colors import BLACK_COLOR, WHITE_COLOR, PRIMARY_COLOR
from res.dimens import SPACE_MD, TOOLBAR_HEIGHT
from res.strings import (
    APP_NAME,
    TOOLTIP_NOTIFICATIONS,
    ADD_NEW_BUTTON_TXT,
    TOOLTIP_MY_PROFILE,
)
from res.fonts import HEADLINE_4_SIZE, HEADLINE_FONT


def get_top_bar(
    on_click_new_btn: Callable,
    on_click_notifications_btn: Callable,
    on_click_profile_btn: Callable,
):
    return Container(
        bgcolor=BLACK_COLOR,
        alignment=alignment.center,
        height=TOOLBAR_HEIGHT,
        padding=padding.symmetric(horizontal=SPACE_MD),
        content=Row(
            alignment=SPACE_BETWEEN_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[
                Row(
                    controls=[
                        get_app_logo(width=10),
                        Text(
                            APP_NAME,
                            size=HEADLINE_4_SIZE,
                            font_family=HEADLINE_FONT,
                            color=WHITE_COLOR,
                        ),
                    ],
                    alignment=CENTER_ALIGNMENT,
                    vertical_alignment=CENTER_ALIGNMENT,
                ),
                Row(
                    controls=[
                        ElevatedButton(
                            text=ADD_NEW_BUTTON_TXT,
                            icon=icons.ADD_OUTLINED,
                            icon_color=PRIMARY_COLOR,
                            color=PRIMARY_COLOR,
                            on_click=on_click_new_btn,
                        ),
                        IconButton(
                            icons.NOTIFICATIONS,
                            icon_color=PRIMARY_COLOR,
                            icon_size=20,
                            tooltip=TOOLTIP_NOTIFICATIONS,
                            on_click=on_click_notifications_btn,
                        ),
                        IconButton(
                            icons.PERSON_OUTLINE_OUTLINED,
                            icon_color=PRIMARY_COLOR,
                            icon_size=20,
                            tooltip=TOOLTIP_MY_PROFILE,
                            on_click=on_click_profile_btn,
                        ),
                    ]
                ),
            ],
        ),
    )
