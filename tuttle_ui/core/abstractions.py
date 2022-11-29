import typing
from abc import ABC, abstractmethod
from typing import Callable
from .constants_and_enums import AlertDialogControls, START_ALIGNMENT, AUTO_SCROLL
from flet import AlertDialog


class ClientStorage(ABC):
    """An abstraction that defines methods for caching data"""

    def __init__(
        self,
    ):
        super().__init__()
        self.keys_prefix = "tuttle_app"

    @abstractmethod
    def set_value(self, key: str, value: any):
        """appends an identifier prefix to the key and stores the key-value pair
        value can be a string, number, boolean or list
        """
        pass

    @abstractmethod
    def get_value(self, key: str) -> typing.Optional[any]:
        """appends an identifier prefix to the key and gets the value if exists"""
        pass

    @abstractmethod
    def remove_value(self, key: str):
        """appends an identifier prefix to the key and removes associated key-value pair if exists"""
        pass


class TuttleView(ABC):
    """Abstract class for all UI screens"""

    def __init__(
        self,
        navigate_to_route: Callable,
        show_snack: Callable,
        dialog_controller: Callable,
        vertical_alignment_in_parent: str = START_ALIGNMENT,
        horizontal_alignment_in_parent: str = START_ALIGNMENT,
        keep_back_stack=True,
        on_navigate_back: typing.Optional[Callable] = None,
        page_scroll_type: typing.Optional[str] = AUTO_SCROLL,
    ):
        super().__init__()
        self.navigate_to_route = navigate_to_route
        self.show_snack = show_snack
        self.dialog_controller = dialog_controller
        self.vertical_alignment_in_parent = vertical_alignment_in_parent
        self.horizontal_alignment_in_parent = horizontal_alignment_in_parent
        self.keep_back_stack = keep_back_stack
        self.on_navigate_back = on_navigate_back
        self.page_scroll_type = page_scroll_type

    def parent_intent_listener(self, intent: str, data: any):
        """listens for an intent from parent view"""
        return None

    def window_on_resized(self, width, height):
        self.page_width = width
        self.page_height = height


class DialogHandler(ABC):
    """Used by views to set, open, and dismiss dialogs"""

    def __init__(
        self,
        dialog: AlertDialog,
        dialog_controller: Callable[[any, AlertDialogControls], None],
    ):
        super().__init__()
        self.dialog_controller = dialog_controller
        self.dialog: AlertDialog = dialog

    def close_dialog(self, e: typing.Optional[any] = None):
        self.dialog_controller(self.dialog, AlertDialogControls.CLOSE)

    def open_dialog(self, e: typing.Optional[any] = None):
        self.dialog_controller(self.dialog, AlertDialogControls.ADD_AND_OPEN)

    def dimiss_open_dialogs(self):
        if self.dialog is not None and self.dialog.open:
            self.close_dialog()
