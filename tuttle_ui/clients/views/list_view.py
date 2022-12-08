import typing
from typing import Callable
from core.constants_and_enums import AlertDialogControls

from core.constants_and_enums import ALWAYS_SCROLL
from flet import (
    UserControl,
    Card,
    Column,
    Container,
    GridView,
    ResponsiveRow,
    Text,
    padding,
)

from core.models import IntentResult
from core.views import horizontal_progress, mdSpace, get_headline_txt

from res.colors import ERROR_COLOR
from res.fonts import HEADLINE_4_SIZE
from res.dimens import SPACE_MD, SPACE_STD
from res.strings import (
    MY_CLIENTS,
    NO_CLIENTS_ADDED,
    NEW_CLIENT_ADDED_SUCCESS,
    UPDATING_CLIENT_SUCCESS,
    UPDATING_CLIENT_FAILED,
)
from clients.intent_impl import ClientsIntentImpl
from .client_card import ClientCard
from res.utils import ADD_CLIENT_INTENT
from clients.client_model import Client
from core.abstractions import TuttleView
from .client_editor import ClientEditorPopUp


class ClientsListView(TuttleView, UserControl):
    def __init__(
        self,
        navigate_to_route,
        show_snack,
        dialog_controller,
        local_storage,
    ):
        super().__init__(
            navigate_to_route=navigate_to_route,
            show_snack=show_snack,
            dialog_controller=dialog_controller,
        )
        self.intent_handler = ClientsIntentImpl(local_storage=local_storage)
        self.loading_indicator = horizontal_progress
        self.no_clients_control = Text(
            value=NO_CLIENTS_ADDED, color=ERROR_COLOR, visible=False
        )
        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        get_headline_txt(txt=MY_CLIENTS, size=HEADLINE_4_SIZE),
                        self.loading_indicator,
                        self.no_clients_control,
                    ],
                )
            ]
        )
        self.clients_container = GridView(
            expand=False,
            max_extent=540,
            child_aspect_ratio=1.0,
            spacing=SPACE_STD,
            run_spacing=SPACE_MD,
        )
        self.clients_to_display = {}
        self.contacts = {}
        self.editor = None

    def parent_intent_listener(self, intent: str, data: any):
        if intent == ADD_CLIENT_INTENT:
            if self.editor is not None:
                self.editor.close_dialog()
            self.editor = ClientEditorPopUp(
                self.dialog_controller,
                on_submit=self.on_save_client,
                contacts_map=self.contacts,
            )
            self.editor.open_dialog()
        return

    def load_all_clients(self):
        self.clients_to_display = self.intent_handler.get_all_clients_as_map()

    def load_all_contacts(self):
        self.contacts = self.intent_handler.get_all_contacts_as_map()

    def refresh_clients(self):
        self.clients_container.controls.clear()
        for key in self.clients_to_display:
            client = self.clients_to_display[key]
            clientCard = ClientCard(client=client, on_edit=self.on_edit_client_clicked)
            self.clients_container.controls.append(clientCard)

    def on_edit_client_clicked(self, client: Client):
        if self.editor is not None:
            self.editor.close_dialog()
        self.editor = ClientEditorPopUp(
            self.dialog_controller,
            on_submit=self.on_save_client,
            contacts_map=self.contacts,
            client=client,
        )
        self.editor.open_dialog()

    def on_save_client(self, client_to_save: Client):
        is_updating = client_to_save.id is not None
        self.loading_indicator.visible = True
        if self.mounted:
            self.update()
        result: IntentResult = self.intent_handler.save_client(client_to_save)
        if not result.was_intent_successful:
            self.show_snack(result.error_msg, True)
        else:
            self.clients_to_display[result.data.id] = result.data
            self.refresh_clients()
            msg = UPDATING_CLIENT_SUCCESS if is_updating else NEW_CLIENT_ADDED_SUCCESS
            self.show_snack(msg, False)
        self.loading_indicator.visible = False
        if self.mounted:
            self.update()

    def show_no_clients(self):
        self.no_clients_control.visible = True

    def did_mount(self):
        try:
            self.mounted = True
            self.loading_indicator.visible = True
            self.load_all_clients()
            count = len(self.clients_to_display)
            self.loading_indicator.visible = False
            if count == 0:
                self.show_no_clients()
            else:
                self.refresh_clients()
            self.load_all_contacts()
            self.update()
        except Exception as e:
            # log
            print(f"exception raised @clients.did_mount {e}")

    def build(self):
        view = Column(
            controls=[
                self.title_control,
                mdSpace,
                Container(self.clients_container, expand=True),
            ],
        )
        return view

    def will_unmount(self):
        try:
            self.mounted = False
            if self.editor:
                self.editor.dimiss_open_dialogs()
        except Exception as e:
            print(e)
