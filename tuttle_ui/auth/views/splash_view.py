from flet import Column, Container, padding, UserControl

"""Displays quick info about Tuttle app"""

from core.views import get_image, mdSpace, get_headline_with_subtitle
from core.constants_and_enums import (
    TXT_ALIGN_CENTER,
    CENTER_ALIGNMENT,
    START_ALIGNMENT,
)
from res import dimens, strings
from res.fonts import HEADLINE_3_SIZE, HEADLINE_4_SIZE
from res.image_paths import splashImgPath


class SplashView(UserControl):
    def build(self):
        view = Column(
            alignment=START_ALIGNMENT,
            horizontal_alignment=CENTER_ALIGNMENT,
            expand=True,
            controls=[
                mdSpace,
                get_image(splashImgPath, strings.SPLASH_IMG_SEMANTIC_LBL, width=300),
                get_headline_with_subtitle(
                    strings.APP_NAME,
                    strings.APP_DESCRIPTION,
                    alignmentInContainer=CENTER_ALIGNMENT,
                    txtAlignment=TXT_ALIGN_CENTER,
                    titleSize=HEADLINE_3_SIZE,
                    subtitleSize=HEADLINE_4_SIZE,
                ),
            ],
        )

        return view
