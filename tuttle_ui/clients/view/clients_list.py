import typing
from typing import Callable

from flet import Card, Column, Container, GridView, ResponsiveRow, Text, padding

from core.abstractions import LocalCache
from core.views.progress_bars import (
    horizontalProgressBar,
)
from res.utils import CLIENT_DETAILS_SCREEN_ROUTE
from core.views.spacers import mdSpace
from core.views.texts import get_headline_txt
from clients.abstractions import ClientDestinationView
from res.colors import ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_MD, SPACE_STD
from res.strings import MY_CLIENTS, NO_CLIENTS_ADDED
from clients.client_intents_impl import ClientIntentImpl
from .client_card import ClientCard


class ClientsListView(ClientDestinationView):
    def __init__(
        self,
        localCacheHandler: LocalCache,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
    ):
        super().__init__(
            intentHandler=ClientIntentImpl(cache=localCacheHandler),
            onChangeRouteCallback=onChangeRouteCallback,
        )
        self.progressBar = horizontalProgressBar
        self.noClientsComponent = Text(
            value=NO_CLIENTS_ADDED, color=ERROR_COLOR, visible=False
        )
        self.titleComponent = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt=MY_CLIENTS, size=HEADLINE_4_SIZE),
                        self.progressBar,
                        self.noClientsComponent,
                    ],
                )
            ]
        )
        self.clientsContainer = GridView(
            expand=False,
            max_extent=300,
            child_aspect_ratio=1.0,
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.clientsToDisplay = {}

    def load_all_clients(self):
        self.clientsToDisplay = self.intentHandler.get_all_clients()

    def display_currently_filtered_clients(self):
        self.clientsContainer.controls.clear()
        for key in self.clientsToDisplay:
            client = self.clientsToDisplay[key]
            clientCard = ClientCard(
                client=client, onClickView=self.on_view_client_clicked
            )
            self.clientsContainer.controls.append(clientCard)

    def on_view_client_clicked(self, clientId: str):
        self.changeRoute(CLIENT_DETAILS_SCREEN_ROUTE, clientId)

    def show_no_clients(self):
        self.noClientsComponent.visible = True

    def did_mount(self):
        self.load_all_clients()
        count = len(self.clientsToDisplay)
        self.progressBar.visible = False
        if count == 0:
            self.show_no_clients()
        else:
            self.display_currently_filtered_clients()
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
                        Container(height=600, content=self.clientsContainer),
                    ]
                ),
            ),
        )
        return view
