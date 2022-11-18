from flet import Column, Container, padding

"""Displays quick info about Tuttle app"""

from core.ui.components.images import images
from core.ui.components.spacers import mdSpace
from core.ui.utils.flet_constants import (
    TXT_ALIGN_CENTER,
    CENTER_ALIGNMENT,
    START_ALIGNMENT,
)
from res import spacing, strings
from res.fonts import HEADLINE_3_SIZE, HEADLINE_4_SIZE
from res.image_paths import splashImgPath
from core.ui.components.text import headlines

splashSection = Container(
    col={"xs": 12, "md": 6},
    padding=padding.all(spacing.SPACE_XS),
    content=Column(
        alignment=START_ALIGNMENT,
        horizontal_alignment=CENTER_ALIGNMENT,
        expand=True,
        controls=[
            mdSpace,
            images.get_image(splashImgPath, strings.SPLASH_IMG_SEMANTIC_LBL, width=300),
            headlines.get_headline_with_subtitle(
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
