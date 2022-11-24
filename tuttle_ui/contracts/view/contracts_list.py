import typing
from typing import Callable

from flet import Card, Column, Container, GridView, ResponsiveRow, Text, padding

from core.abstractions import LocalCache
from core.views.progress_bars import (
    horizontalProgressBar,
)
from res.utils import CONTRACT_DETAILS_SCREEN_ROUTE
from core.views.spacers import mdSpace
from core.views.texts import get_headline_txt
from contracts.abstractions import ContractDestinationView
from res.colors import ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_MD, SPACE_STD
from res.strings import MY_CONTRACTS, NO_CONTRACTS_ADDED
from contracts.contract_intents_impl import ContractIntentImpl
from .contract_card import ContractCard
from .contracts_filters import ContractFiltersView, ContractStates


class ContractsListView(ContractDestinationView):
    def __init__(
        self,
        localCacheHandler: LocalCache,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
    ):
        super().__init__(
            intentHandler=ContractIntentImpl(cache=localCacheHandler),
            onChangeRouteCallback=onChangeRouteCallback,
        )
        self.progressBar = horizontalProgressBar
        self.noContractsComponent = Text(
            value=NO_CONTRACTS_ADDED, color=ERROR_COLOR, visible=False
        )
        self.titleComponent = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt=MY_CONTRACTS, size=HEADLINE_4_SIZE),
                        self.progressBar,
                        self.noContractsComponent,
                    ],
                )
            ]
        )
        self.contractsContainer = GridView(
            expand=False,
            max_extent=480,
            child_aspect_ratio=1.0,
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.contractsToDisplay = {}

    def load_all_contracts(self):
        self.contractsToDisplay = self.intentHandler.get_all_contracts()

    def display_currently_filtered_contracts(self):
        self.contractsContainer.controls.clear()
        for key in self.contractsToDisplay:
            contract = self.contractsToDisplay[key]
            contractCard = ContractCard(
                contract=contract, onClickView=self.on_view_contract_clicked
            )
            self.contractsContainer.controls.append(contractCard)

    def on_view_contract_clicked(self, contractId: str):
        self.changeRoute(CONTRACT_DETAILS_SCREEN_ROUTE, contractId)

    def on_filter_contracts(self, filterByState: ContractStates):
        if filterByState.value == ContractStates.ACTIVE.value:
            self.contractsToDisplay = self.intentHandler.get_active_contracts()
        elif filterByState.value == ContractStates.UPCOMING.value:
            self.contractsToDisplay = self.intentHandler.get_upcoming_contracts()
        elif filterByState.value == ContractStates.COMPLETED.value:
            self.contractsToDisplay = self.intentHandler.get_completed_contracts()
        else:
            self.contractsToDisplay = self.intentHandler.get_all_contracts()
        self.display_currently_filtered_contracts()
        self.update()

    def show_no_contracts(self):
        self.noContractsComponent.visible = True

    def did_mount(self):
        self.load_all_contracts()
        count = len(self.contractsToDisplay)
        self.progressBar.visible = False
        if count == 0:
            self.show_no_contracts()
        else:
            self.display_currently_filtered_contracts()
        self.update()

    def build(self):
        view = Card(
            expand=True,
            content=Container(
                expand=True,
                padding=padding.all(SPACE_MD),
                content=Column(
                    controls=[
                        self.titleComponent,
                        mdSpace,
                        ContractFiltersView(onStateChanged=self.on_filter_contracts),
                        mdSpace,
                        Container(height=600, content=self.contractsContainer),
                    ]
                ),
            ),
        )
        return view
