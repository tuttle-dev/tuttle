"""Defines the app theme"""

from flet import theme
from .fonts import DEFAULT_FONT
from .colors import PRIMARY_COLOR
from enum import Enum

from tuttle.dev import deprecated


class THEME_MODES(Enum):
    light = "light"
    dark = "dark"

    def __str__(self) -> str:
        return str(self.value)


def get_theme_mode_from_value(value: str):
    return next((e for e in THEME_MODES if e.value == value), None)


APP_THEME = theme.Theme(
    color_scheme_seed=PRIMARY_COLOR,
    use_material3=True,
    font_family=DEFAULT_FONT,
    visual_density="adaptivePlatformDensity",
)
