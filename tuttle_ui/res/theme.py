"""Defines the app theme"""

from flet import theme
from .fonts import ALL_FONTS, DEFAULT_FONT
from .colors import PRIMARY_COLOR
from enum import Enum


class THEME_MODES(Enum):
    system = "system"
    light = "light"
    dark = "dark"

    def __str__(self) -> str:
        return str(self.value)


def get_theme_mode_from_value(value: str):
    if value == THEME_MODES.system.value:
        return THEME_MODES.system
    elif value == THEME_MODES.dark.value:
        return THEME_MODES.dark
    else:
        return THEME_MODES.light


APP_THEME = theme.Theme(
    color_scheme_seed=PRIMARY_COLOR,
    use_material3=True,
    font_family=DEFAULT_FONT,
    visual_density="adaptivePlatformDensity",
)

APP_FONTS = ALL_FONTS
