from flet import theme
from .fonts import ALL_FONTS, DEFAULT_FONT
from .colors import PRIMARY_COLOR

APP_THEME_MODE = "light"

APP_THEME = theme.Theme(
    color_scheme_seed=PRIMARY_COLOR,
    use_material3=True,
    font_family= DEFAULT_FONT
)

APP_FONTS = ALL_FONTS
