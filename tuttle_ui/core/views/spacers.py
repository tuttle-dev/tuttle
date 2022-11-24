"""Empty containers that serve as space between Ui components"""

from res import spacing
from flet import Container

stdSpace = Container(
    height=spacing.SPACE_STD, width=spacing.SPACE_STD, padding=0, margin=0
)

mdSpace = Container(
    height=spacing.SPACE_MD, width=spacing.SPACE_MD, padding=0, margin=0
)

smSpace = Container(
    height=spacing.SPACE_SM, width=spacing.SPACE_SM, padding=0, margin=0
)

xsSpace = Container(
    height=spacing.SPACE_XS, width=spacing.SPACE_XS, padding=0, margin=0
)
