from enum import Enum

from flet import Container, icons

from res.strings import INVOICING, SECONDARY_MENU_GROUP_TITLE, TIME_TRACKING


class SecondaryMenuItems(Enum):
    """Specifies the secondary menu items mapped to a zero based index"""

    TIME_TRACKING = 0
    INVOICING = 1
    DATATABLE_DEMO = 2


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
        if item.value == SecondaryMenuItems.TIME_TRACKING.value:
            return TIME_TRACKING
        elif item.value == SecondaryMenuItems.INVOICING.value:
            return INVOICING
        elif item.value == SecondaryMenuItems.DATATABLE_DEMO.value:
            return "Datatable"

    def get_secondary_menu_item_icon(self, item: SecondaryMenuItems) -> str:
        """returns the un-selected-state-icon given a menu item"""
        if item.value == SecondaryMenuItems.TIME_TRACKING.value:
            return icons.TIMER
        elif item.value == SecondaryMenuItems.INVOICING.value:
            return icons.ATTACH_MONEY
        elif item.value == SecondaryMenuItems.DATATABLE_DEMO.value:
            return icons.TABLE_CHART

    def get_secondary_menu_item_selected_icon(self, item: SecondaryMenuItems) -> str:
        """returns the selected-state-icon given a menu item"""
        if item.value == SecondaryMenuItems.TIME_TRACKING.value:
            return icons.TIMER_ROUNDED
        elif item.value == SecondaryMenuItems.INVOICING.value:
            return icons.ATTACH_MONEY_ROUNDED
        elif item.value == SecondaryMenuItems.DATATABLE_DEMO.value:
            return icons.TABLE_CHART_ROUNDED

    def get_secondary_menu_item_from_index(self, index: int) -> SecondaryMenuItems:
        """Given an integer index, returns the corresponding side menu item"""
        if index == SecondaryMenuItems.TIME_TRACKING.value:
            return SecondaryMenuItems.TIME_TRACKING
        elif index == SecondaryMenuItems.INVOICING.value:
            return SecondaryMenuItems.INVOICING
        elif index == SecondaryMenuItems.DATATABLE_DEMO.value:
            return SecondaryMenuItems.DATATABLE_DEMO

    def get_secondary_menu_destination_view_for_item(self, menu_item):
        """Given a sidemenu item, returns the corresponding view"""
        return Container()

    def get_new_secondary_item_route_or_intent(self, menu_item: SecondaryMenuItems):
        """Given a menu item, returns route for the view responsible for creating the corresponding item"""
        return None
