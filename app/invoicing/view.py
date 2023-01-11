from flet import Column, Container, ResponsiveRow, UserControl

from core import views
from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from core.models import IntentResult
from core.utils import AlertDialogControls
from res import colors, fonts

from .intent import InvoicingIntent


class InvoicingView(TuttleView, UserControl):
    def __init__(
        self,
        params: TuttleViewParams,
    ):
        super().__init__(params)
        self.intent_handler = InvoicingIntent()

        self.title_control = ResponsiveRow(
            controls=[
                Column(
                    col={"xs": 12},
                    controls=[
                        views.get_headline_txt(
                            txt="Invoicing", size=fonts.HEADLINE_4_SIZE
                        ),
                    ],
                )
            ]
        )

    def build(self):

        view = Column(
            controls=[
                self.title_control,
                views.mdSpace,
            ]
        )
        return view
