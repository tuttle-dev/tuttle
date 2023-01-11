from flet import (
    UserControl,
)

from core.abstractions import DialogHandler, TuttleView, TuttleViewParams
from core.utils import AlertDialogControls
from core.models import IntentResult

from .intent import InvoicingIntent


class InvoicingView(TuttleView, UserControl):
    def __init__(
        self,
        params: TuttleViewParams,
    ):
        super().__init__(params)
        self.intent_handler = InvoicingIntent()
