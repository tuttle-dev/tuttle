from flet import Image, Container, Row
from res import image_paths
from core.ui.utils.flet_constants import CONTAIN
from res import fonts, strings, colors
from core.ui.components.images import app_logo
from core.ui.components.text import headlines


def get_app_logo(width: int = 12):
    """Returns app logo"""
    return Container(
        width=width,
        content=Image(src=image_paths.logoPath, fit=CONTAIN, semantics_label="logo"),
    )


# A logo with app name as label
labelledLogo = Row(
    vertical_alignment="center",
    controls=[
        app_logo.get_app_logo(),
        headlines.get_headline_txt(
            strings.APP_NAME, size=fonts.HEADLINE_3_SIZE, color=colors.BLACK_COLOR
        ),
    ],
)
