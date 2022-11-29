from core.abstractions import TuttleView
from typing import Callable
from flet import UserControl, Column, Container, padding
from core.constants_and_enums import CENTER_ALIGNMENT
from core.views import get_error_txt, get_primary_btn
from res.strings import PAGE_NOT_FOUND, GO_BACK
from res.dimens import SPACE_MD, SPACE_STD


class Error404Screen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route: Callable,
        show_snack: Callable,
        dialog_controller: Callable,
        on_navigate_back: Callable,
    ):
        super().__init__(
            navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
            vertical_alignment_in_parent=CENTER_ALIGNMENT,
            horizontal_alignment_in_parent=CENTER_ALIGNMENT,
            on_navigate_back=on_navigate_back,
        )

    def build(self):
        view = Container(
            Column(
                expand=True,
                spacing=SPACE_STD,
                run_spacing=SPACE_STD,
                controls=[
                    get_error_txt(PAGE_NOT_FOUND),
                    get_primary_btn(
                        label=GO_BACK.upper(), on_click=self.on_navigate_back
                    ),
                ],
            ),
            padding=padding.all(SPACE_MD),
        )

        return view
