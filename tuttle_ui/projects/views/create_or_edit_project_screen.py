from core.abstractions import TuttleView
from typing import Optional, Callable
from flet import Container, UserControl


class CreateOrEditProjectScreen(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route: Callable,
        intent_handler,
        show_snack: Callable,
        dialog_controller: Callable,
        vertical_alignment_in_parent: str = ...,
        horizontal_alignment_in_parent: str = ...,
        keep_back_stack=False,
        on_navigate_back: Optional[Callable] = None,
        page_scroll_type: str = ...,
    ):
        super().__init__(
            navigate_to_route,
            intent_handler,
            show_snack,
            dialog_controller,
            vertical_alignment_in_parent,
            horizontal_alignment_in_parent,
            keep_back_stack,
            on_navigate_back,
            page_scroll_type,
        )

    def build(self):
        view = Container(expand=True)
        return view
