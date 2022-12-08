import typing
from typing import Callable

from flet import Card, Column, Container, GridView, ResponsiveRow, Text, padding

from core.constants_and_enums import ALWAYS_SCROLL
from contracts.intent_impl import ContractsIntentImpl
from core.abstractions import ClientStorage
from core.views import get_headline_txt, horizontal_progress, mdSpace
from res.colors import ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.dimens import SPACE_MD, SPACE_STD
from res.strings import MY_CONTRACTS, NO_CONTRACTS_ADDED
from res.utils import CONTRACT_DETAILS_SCREEN_ROUTE

from .contract_card import ContractCard
from .contracts_filters import ContractFiltersView, ContractStates
from core.abstractions import TuttleView
from flet import UserControl


class ContractsListView(TuttleView, UserControl):
    def __init__(self, navigate_to_route, show_snack, dialog_controller, local_storage):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = ContractsIntentImpl(local_storage=local_storage)
        self.loading_indicator = horizontal_progress
        self.no_contracts_control = Text(
            value=NO_CONTRACTS_ADDED, color=ERROR_COLOR, visible=False
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt=MY_CONTRACTS, size=HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.no_contracts_control,
                    ],
                )
            ]
        )
        self.contracts_container = GridView(
            expand=False,
            max_extent=540,
            child_aspect_ratio=1.0,
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.contracts_to_display = {}

    def load_all_contracts(self):
        self.contracts_to_display = self.intent_handler.get_all_contracts_as_map()

    def display_currently_filtered_contracts(self):
        self.contracts_container.controls.clear()
        for key in self.contracts_to_display:
            contract = self.contracts_to_display[key]
            contractCard = ContractCard(
                contract=contract, on_click_view=self.on_view_contract_clicked
            )
            self.contracts_container.controls.append(contractCard)

    def on_view_contract_clicked(self, contractId: str):
        self.navigate_to_route(CONTRACT_DETAILS_SCREEN_ROUTE, contractId)

    def on_filter_contracts(self, filterByState: ContractStates):
        if filterByState.value == ContractStates.ACTIVE.value:
            self.contracts_to_display = self.intent_handler.get_active_contracts()
        elif filterByState.value == ContractStates.UPCOMING.value:
            self.contracts_to_display = self.intent_handler.get_upcoming_contracts()
        elif filterByState.value == ContractStates.COMPLETED.value:
            self.contracts_to_display = self.intent_handler.get_completed_contracts()
        else:
            self.contracts_to_display = self.intent_handler.get_all_contracts()
        self.display_currently_filtered_contracts()
        if self.mounted:
            self.update()

    def show_no_contracts(self):
        self.no_contracts_control.visible = True

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.load_all_contracts()
            count = len(self.contracts_to_display)
            self.loading_indicator.visible = False
            if count == 0:
                self.show_no_contracts()
            else:
                self.display_currently_filtered_contracts()
            if self.mounted:
                self.update()
        except Exception as e:
            # log error
            print(f"exception raised @contracts.did_mount {e}")

    def build(self):
        view = Column(
            controls=[
                self.title_control,
                mdSpace,
                ContractFiltersView(onStateChanged=self.on_filter_contracts),
                mdSpace,
                Container(self.contracts_container, expand=True),
            ]
        )
        return view

    def will_unmount(self):
        self.mounted = False
