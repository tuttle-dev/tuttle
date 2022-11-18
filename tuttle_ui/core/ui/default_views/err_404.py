from typing import Callable

from flet import Text, ResponsiveRow, UserControl
from core.abstractions.view import TuttleView
from core.ui.utils.flet_constants import CENTER_ALIGNMENT
from res import spacing
from core.abstractions.local_cache import LocalCache
import typing


class Error404Screen(TuttleView, UserControl):
    """Page not found screen"""

    def __init__(
        self, changeRouteCallback: Callable[[str, typing.Optional[any]], None]
    ):
        super().__init__(
            hasFloatingActionBtn=False,
            hasAppBar=False,
            onChangeRouteCallback=changeRouteCallback,
        )

    def build(self):
        """Called when page is built"""
        page_view = ResponsiveRow(
            spacing=0,
            run_spacing=0,
            alignment=CENTER_ALIGNMENT,
            vertical_alignment=CENTER_ALIGNMENT,
            controls=[Text("Page Not Found")],
        )
        page_view.padding = spacing.SPACE_STD
        return page_view
