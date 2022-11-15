from abc import ABC, abstractmethod
from typing import Callable

from res.colors import WHITE_COLOR

from .intent import Intent


class TuttleScreen(ABC):
    """Abstract class for all UI screens"""
    def __init__(self, hasFloatingActionBtn : bool, hasAppBar : bool, bgColor : str = WHITE_COLOR):
        super().__init__()
        self.has_floating_action_btn = hasFloatingActionBtn,
        self.has_app_bar = hasAppBar,
        self.bg_color = bgColor

    @abstractmethod
    def set_intent_handler(self, intentHandler : Intent):
        """sets the intent object for this view"""
        pass

    @abstractmethod
    def get_floating_action_btn_if_any(self):
        """Returns a floating action button OR None"""
        pass

    @abstractmethod
    def get_app_bar_if_any(self):
        """Returns an app bar OR None"""
        pass

    @abstractmethod
    def set_route_to_callback(self, onChangeRouteCallback : Callable[[str], None]):
        """Uses a callback to change destination toRoute"""
        pass

   