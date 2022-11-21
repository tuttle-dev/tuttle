from flet import Container, Image, Row

from res import colors, fonts, image_paths, strings

from .flet_constants import CONTAIN
from .texts import get_headline_txt


def get_image(path: str, semanticLbl: str, width: int):
    return Container(
        width=width, content=Image(src=path, fit=CONTAIN, semantics_label=semanticLbl)
    )


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
        get_app_logo(),
        get_headline_txt(
            strings.APP_NAME, size=fonts.HEADLINE_3_SIZE, color=colors.BLACK_COLOR
        ),
    ],
)
