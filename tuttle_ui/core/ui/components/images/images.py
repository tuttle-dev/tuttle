from flet import Image, Container
from core.ui.utils.flet_constants import CONTAIN


def get_image(path: str, semanticLbl: str, width: int):
    return Container(
        width=width, content=Image(src=path, fit=CONTAIN, semantics_label=semanticLbl)
    )
