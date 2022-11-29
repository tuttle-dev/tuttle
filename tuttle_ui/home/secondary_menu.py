from enum import Enum

from flet import Container, icons

from res.strings import INVOICE, SECONDARY_MENU_GROUP_TITLE


class SecondaryMenuItems(Enum):
    """Specifies the secondary menu items mapped to a zero based index"""

    INVOICE = 0


class SecondaryMenuHandler:
    """Manages home's side menu"""

    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        local_storage,
    ):
        super().__init__()
        self.first_item_index = 0
        self.secondary_menu_title = SECONDARY_MENU_GROUP_TITLE

    def get_secondary_menu_item_lbl(self, item: SecondaryMenuItems) -> str:
        """returns a label given a secondary menu item"""
        return INVOICE

    def get_secondary_menu_item_icon(self, item: SecondaryMenuItems) -> str:
        """returns the un-selected-state-icon given a menu item"""
        return icons.ATTACH_MONEY_OUTLINED

    def get_secondary_menu_item_selected_icon(self, item: SecondaryMenuItems) -> str:
        """returns the selected-state-icon given a menu item"""
        return icons.ATTACH_MONEY_ROUNDED

    def get_secondary_menu_item_from_index(self, index: int) -> SecondaryMenuItems:
        """Given an integer index, returns the corresponding side menu item"""
        return SecondaryMenuItems.INVOICE

    def get_secondary_menu_destination_view_for_item(self, menu_item):
        """Given a sidemenu item, returns the corresponding view"""
        return Container()

    def get_new_secondary_item_route_or_intent(self, menu_item: SecondaryMenuItems):
        """Given a menu item, returns route for the view responsible for creating the corresponding item"""
        return None
