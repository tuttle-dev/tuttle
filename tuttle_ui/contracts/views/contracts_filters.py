from flet import (
    ButtonStyle,
    ElevatedButton,
    ResponsiveRow,
    UserControl,
)
from typing import Callable
from res.colors import PRIMARY_COLOR, GRAY_COLOR
from res.dimens import CLICKABLE_PILL_HEIGHT
from res.strings import ACTIVE, ALL, COMPLETED, UPCOMING
from core.constants_and_enums import (
    HOVERED,
    OTHER_CONTROL_STATES,
    SELECTED,
    PRESSED,
)
from enum import Enum


class ContractStates(Enum):
    ALL = 1
    ACTIVE = 2
    COMPLETED = 3
    UPCOMING = 4


class ContractFiltersView(UserControl):
    """Create and Handles contracts view filtering buttons"""

    def __init__(self, onStateChanged: Callable[[ContractStates], None]):
        super().__init__()
        self.currentState = ContractStates.ALL
        self.stateTofilterButtonsMap = {}
        self.onStateChangedCallback = onStateChanged

    def filter_button(
        self, state: ContractStates, lbl: str, onClick: Callable[[ContractStates], None]
    ):
        button = ElevatedButton(
            text=lbl,
            col={"xs": 6, "sm": 3, "lg": 2},
            on_click=lambda e: onClick(state),
            height=CLICKABLE_PILL_HEIGHT,
            color=PRIMARY_COLOR if state == self.currentState else GRAY_COLOR,
            style=ButtonStyle(
                elevation={
                    PRESSED: 3,
                    SELECTED: 3,
                    HOVERED: 4,
                    OTHER_CONTROL_STATES: 2,
                },
            ),
        )
        return button

    def on_filter_button_clicked(self, state: ContractStates):
        """sets the new state and updates selected button"""
        self.stateTofilterButtonsMap[self.currentState].color = GRAY_COLOR
        self.currentState = state
        self.stateTofilterButtonsMap[self.currentState].color = PRIMARY_COLOR
        self.update()
        self.onStateChangedCallback(state)

    def get_filter_button_lbl(self, state: ContractStates):
        if state.value == ContractStates.ACTIVE.value:
            return ACTIVE
        elif state.value == ContractStates.UPCOMING.value:
            return UPCOMING
        elif state.value == ContractStates.COMPLETED.value:
            return COMPLETED
        else:
            return ALL

    def set_filter_buttons(self):
        for state in ContractStates:
            button = self.filter_button(
                lbl=self.get_filter_button_lbl(state),
                state=state,
                onClick=self.on_filter_button_clicked,
            )
            self.stateTofilterButtonsMap[state] = button

    def build(self):
        if len(self.stateTofilterButtonsMap) == 0:
            # set the buttons
            self.set_filter_buttons()

        self.filters = ResponsiveRow(
            controls=list(self.stateTofilterButtonsMap.values())
        )
        return self.filters
