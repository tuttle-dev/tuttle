import typing
from typing import Callable
from core.views.alert_dialog_controls import AlertDialogControls

from flet import Card, Column, Container, GridView, ResponsiveRow, Text, padding

from core.abstractions import LocalCache
from core.views.progress_bars import (
    horizontalProgressBar,
)
from core.views.spacers import mdSpace
from core.views.texts import get_headline_txt
from clients.abstractions import ClientDestinationView
from res.colors import ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.spacing import SPACE_MD, SPACE_STD
from res.strings import (
    MY_CLIENTS,
    NO_CLIENTS_ADDED,
    NEW_CLIENT_ADDED_SUCCESS,
    UPDATING_CLIENT_SUCCESS,
    UPDATING_CLIENT_FAILED,
)
from clients.client_intents_impl import ClientIntentImpl
from .client_card import ClientCard
from res.utils import ADD_CLIENT_INTENT
from clients.utils import ClientIntentsResult
from .client_editor import EditClientPopUp
from clients.client_model import Client


class ClientsListView(ClientDestinationView):
    def __init__(
        self,
        localCacheHandler: LocalCache,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
        showSnackCallback=Callable,
        pageDialogController=AlertDialogControls,
    ):
        super().__init__(
            intentHandler=ClientIntentImpl(cache=localCacheHandler),
            onChangeRouteCallback=onChangeRouteCallback,
        )
        self.pageDialogController = pageDialogController
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
        self.showSnack = showSnackCallback
        self.editor = None

    def parent_intent_listener(self, intent: str, data: any):
        if intent == ADD_CLIENT_INTENT:
            """New client was clicked"""
            clientTitle = data
            self.progressBar.visible = True
            self.update()
            result: ClientIntentsResult = self.intentHandler.create_client(
                title=clientTitle
            )
            if not result.wasIntentSuccessful:
                self.showSnack(result.errorMsg, True)
            else:
                client = result.data
                self.clientsToDisplay[client.id] = client
                self.refresh_clients()
                self.showSnack(NEW_CLIENT_ADDED_SUCCESS, False)
            self.progressBar.visible = False
            self.update()
        return

    def load_all_clients(self):
        self.clientsToDisplay = self.intentHandler.get_all_clients()

    def load_all_contacts(self):
        self.contacts = {}
        result = self.intentHandler.get_all_contacts_as_map()
        if result.wasIntentSuccessful:
            self.contacts = result.data

    def refresh_clients(self):
        self.clientsContainer.controls.clear()
        for key in self.clientsToDisplay:
            client = self.clientsToDisplay[key]
            clientCard = ClientCard(
                client=client, onClickView=self.on_edit_client_clicked
            )
            self.clientsContainer.controls.append(clientCard)

    def on_edit_client_clicked(self, clientId: str):
        if self.editor is not None:
            self.editor.close_dialog()
        else:
            self.editor = EditClientPopUp(
                self.pageDialogController,
                client=self.clientsToDisplay[clientId],
                onSubmit=self.on_update_client,
                contacts=self.contacts,
            )
        self.editor.open_dialog()

    def on_update_client(self, client: Client):
        result = self.intentHandler.update_client(client)
        if result.wasIntentSuccessful:
            self.clientsToDisplay[client.id] = client
            self.refresh_clients()
            self.showSnack(UPDATING_CLIENT_SUCCESS, True)
        else:
            # show error
            self.showSnack(UPDATING_CLIENT_FAILED, True)
        self.update()

    def show_no_clients(self):
        self.noClientsComponent.visible = True

    def did_mount(self):
        self.load_all_clients()
        count = len(self.clientsToDisplay)
        self.progressBar.visible = False
        if count == 0:
            self.show_no_clients()
        else:
            self.load_all_contacts()
            self.refresh_clients()
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

    def will_unmount(self):
        try:
            if self.editor:
                self.editor.dimiss_open_dialogs()
        except Exception as e:
            print(e)
