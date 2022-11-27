from flet import Column, Container, padding

"""Displays quick info about Tuttle app"""

from core.views.images import get_image
from core.views.spacers import mdSpace
from core.views.flet_constants import (
    TXT_ALIGN_CENTER,
    CENTER_ALIGNMENT,
    START_ALIGNMENT,
)
from res import spacing, strings
from res.fonts import HEADLINE_3_SIZE, HEADLINE_4_SIZE
from res.image_paths import splashImgPath
from core.views.texts import get_headline_with_subtitle

splashSection = Container(
    col={"xs": 12, "md": 6},
    padding=padding.all(spacing.SPACE_XS),
    content=Column(
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
    ),
)
