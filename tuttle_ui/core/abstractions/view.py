from abc import ABC
import typing
from typing import Callable

from res.colors import WHITE_COLOR

from .intent import Intent


class TuttleView(ABC):
    """Abstract class for all UI screens

    onChangeRouteCallback - used to route to a new destination
    intentHandler - optional Intent object for communicating with dataSource
    hasFloatingActionBtn - if screen has a floating action button, default is False
    hasAppBar - if screen has an appbar, default is False
    bgColor - background color, default is [WHITE_COLOR]
    """

    def __init__(
        self,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
        intentHandler: typing.Optional[Intent] = None,
        hasFloatingActionBtn: bool = False,
        hasAppBar: bool = False,
        bgColor: str = WHITE_COLOR,
    ):
        super().__init__()
        self.has_floating_action_btn = (hasFloatingActionBtn,)
        self.has_app_bar = (hasAppBar,)
        self.bg_color = (bgColor,)
        self.changeRoute = onChangeRouteCallback
        self.intentHandler = intentHandler

    def get_floating_action_btn_if_any(self):
        """Returns a floating action button OR None"""
        return None

    def get_app_bar_if_any(self):
        """Returns an app bar OR None"""
        return None
