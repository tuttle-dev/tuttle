from typing import Callable

from flet import AlertDialog, Column, Container
from core.abstractions import DialogHandler
from core.views import texts
from core.views.alert_dialog_controls import AlertDialogControls
from core.views.buttons import get_primary_btn
from core.views.spacers import mdSpace
from res.dimens import MIN_WINDOW_WIDTH


class NewClientPopUp(DialogHandler):
    def __init__(
        self,
        dialogController: Callable[[any, AlertDialogControls], None],
        onSubmit: Callable,
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
                            lbl="Client Title",
                            hint="",
                        ),
                    ]
                ),
                height=160,
                width=int(MIN_WINDOW_WIDTH * 0.8),
            ),
            actions=[get_primary_btn(label="Add Client", onClickCallback=self.on_add)],
        )
        super().__init__(dialog, dialogController)
        self.clientTitle = ""
        self.onClientSet = onSubmit

    def on_client_title_changed(self, e):
        self.clientTitle = e.control.value

    def on_add(self, e):
        if self.clientTitle is None:
            return
        self.close_dialog()
        self.onClientSet(self.clientTitle)
