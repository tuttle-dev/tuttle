from typing import Callable, Mapping

from flet import AlertDialog, Column, Container
from core.abstractions import DialogHandler
from core.views.texts import get_std_txt_field, get_headline_with_subtitle
from core.views.selectors import get_dropdown
from core.views.alert_dialog_controls import AlertDialogControls
from core.views.buttons import get_primary_btn
from core.views.spacers import mdSpace
from res.dimens import MIN_WINDOW_WIDTH

from clients.client_model import Client
from contacts.contact_model import Contact


class EditClientPopUp(DialogHandler):
    def __init__(
        self,
        dialogController: Callable[[any, AlertDialogControls], None],
        onSubmit: Callable,
        client: Client,
        contacts: Mapping[str, Contact],
    ):
        self.client = client
        self.contactsDropdownItems = []
        self.clientTitle = self.client.title
        self.invoicingContactId = self.client.invoicing_contact_id
        selectedDropdownItem = ""
        for id in contacts:
            contactName = contacts[id].name
            item = f"#{id} {contactName}"
            if id == self.invoicingContactId:
                selectedDropdownItem = item
            self.contactsDropdownItems.append(item)

        dialog = AlertDialog(
            content=Container(
                content=Column(
                    controls=[
                        get_headline_with_subtitle(
                            title="Client Editor",
                            subtitle="Update client info",
                        ),
                        mdSpace,
                        get_std_txt_field(
                            onChangeCallback=self.on_client_title_changed,
                            lbl="Client title",
                            hint=self.client.title,
                            initialValue=self.client.title,
                        ),
                        get_dropdown(
                            lbl="Invoicing Contact",
                            items=self.contactsDropdownItems,
                            onChange=self.on_contact_selected,
                            initialValue=selectedDropdownItem,
                        ),
                        mdSpace,
                    ]
                ),
                height=180,
                width=int(MIN_WINDOW_WIDTH * 0.8),
            ),
            actions=[
                get_primary_btn(label="Update Client", onClickCallback=self.on_submit)
            ],
        )
        super().__init__(dialog, dialogController)
        self.onSubmitCallback = onSubmit

    def on_client_title_changed(self, e):
        self.clientTitle = e.control.value

    def on_contact_selected(self, e):
        selected = e.control.value
        id = ""
        for c in selected:
            if c == "#":
                continue
            if c == " ":
                break
            id = id + c
        self.invoicingContactId = id

    def on_submit(self, e):
        self.close_dialog()
        # update values or keep previous
        self.client.title = self.clientTitle if self.clientTitle else self.client.title
        self.client.invoicing_contact_id = (
            self.invoicingContactId
            if self.invoicingContactId
            else self.client.invoicing_contact_id
        )
        self.onSubmitCallback(self.client)
