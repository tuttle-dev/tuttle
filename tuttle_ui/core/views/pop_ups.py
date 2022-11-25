from typing import Callable

from flet import AlertDialog, Column, Container, Row


from core.abstractions import DialogHandler
from core.views import texts
from core.views.alert_dialog_controls import AlertDialogControls
from core.views.buttons import get_primary_btn
from core.views.spacers import mdSpace, xsSpace
from res.dimens import MIN_WINDOW_WIDTH
from core.views.flet_constants import CENTER_ALIGNMENT
from res.fonts import HEADLINE_4_SIZE


class NewClientPopUp(DialogHandler):
    def __init__(
        self,
        dialogController: Callable[[any, AlertDialogControls], None],
        onClientSet: Callable,
    ):
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    controls=[
                        texts.get_headline_with_subtitle(
                            title="Create a new client",
                            subtitle="You can add more info later",
                        ),
                        mdSpace,
                        texts.get_std_txt_field(
                            onChangeCallback=self.on_client_title_changed,
                            lbl="Client Name",
                            hint="",
                        ),
                    ]
                ),
                height=200,
                width=int(MIN_WINDOW_WIDTH * 0.8),
            ),
            actions=[get_primary_btn(label="Add Client", onClickCallback=self.on_add)],
        )
        super().__init__(dialog, dialogController)
        self.clientTitle = ""
        self.onClientSet = onClientSet

    def on_client_title_changed(self, e):
        self.clientTitle = e.control.value

    def on_add(self, e):
        if not self.clientTitle:
            return
        self.close_dialog()
        self.onClientSet(self.clientTitle)


class NewContractPopUp(DialogHandler):
    def __init__(
        self,
        dialogController: Callable[[any, AlertDialogControls], None],
        onContractSet: Callable,
    ):
        dialog = AlertDialog(
            content=Container(
                content=Column(
                    controls=[
                        texts.get_headline_with_subtitle(
                            title="Create a new contract",
                            subtitle="You can add more info later",
                        ),
                        mdSpace,
                        texts.get_std_txt_field(
                            onChangeCallback=self.on_contract_title_changed,
                            lbl="Contract title",
                            hint="",
                        ),
                    ]
                ),
                height=300,
                width=int(MIN_WINDOW_WIDTH * 0.8),
            ),
            actions=[
                get_primary_btn(label="Add Contract", onClickCallback=self.on_add)
            ],
        )
        super().__init__(dialog, dialogController)
        self.contractTitle = ""
        self.onContractSet = onContractSet

    def on_contract_title_changed(self, e):
        self.contractTitle = e.control.value

    def on_add(self, e):
        if not self.contractTitle:
            return
        self.close_dialog()
        self.onContractSet(self.contractTitle)
