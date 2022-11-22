import typing
from abc import ABC, abstractmethod
from typing import Callable

from flet import AlertDialog

from core.views.alert_dialog_controls import AlertDialogControls

from .views.flet_constants import START_ALIGNMENT


class LocalCache(ABC):
    """An abstraction that defines methods for caching data"""

    def __init__(
        self,
    ):
        super().__init__()
        self.tuttleKeysPrefix = "tuttle"

    @abstractmethod
    def set_value(self, key: str, value: any):
        """appends an identifier prefix to the key and stores the key-value pair
        value can be a string, number, boolean or list
        """
        pass

    @abstractmethod
    def get_value(self, key: str) -> typing.Optional[any]:
        """appends an identifier prefix to the key and gets the value if exists"""
        pass

    @abstractmethod
    def remove_value(self, key: str):
        """appends an identifier prefix to the key and removes associated key-value pair if exists"""
        pass


class IntentResult(ABC):
    """An absraction that defines the result of a view's intent"""

    def __init__(
        self,
        data,
        wasIntentSuccessful: bool,
        errorMsgIfAny: str = "",
        logMsg: str = "",
    ):
        super().__init__()
        self.errorMsg = errorMsgIfAny
        self.data = data
        self.wasIntentSuccessful = wasIntentSuccessful
        self.logMsg = logMsg


class DataSource(ABC):
    """A simple abstraction that defines a dataSource class"""

    def __init__(
        self,
    ):
        super().__init__()


class Intent(ABC):
    """A simple abstraction that defines an intent class

    cache - provides access to local/client storage
    dataSource - provides access to the data dataSource
    """

    def __init__(self, cache: LocalCache, dataSource: DataSource):
        super().__init__()
        self.cache = cache
        self.dataSource = dataSource


class TuttleDestinationView(ABC):
    """Abstract class for all UI destination screens

    a destination screen does NOT take entire page
    typically added as a tab / navigation rail / bottom nav destination

    onChangeRouteCallback - used to route to a new destination
    intentHandler - optional Intent object for communicating with dataSource
    bgColor - background color, default is [WHITE_COLOR]
    """

    def __init__(
        self,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
        intentHandler: typing.Optional[Intent] = None,
    ):
        super().__init__()
        self.changeRoute = onChangeRouteCallback
        self.intentHandler = intentHandler


class TuttleView(ABC):
    """Abstract class for all UI screens

    onChangeRouteCallback - used to route to a new destination
    intentHandler - optional Intent object for communicating with dataSource
    hasFloatingActionBtn - if screen has a floating action button, default is False
    hasAppBar - if screen has an appbar, default is False
    addDialogToPageCallback - [optional] used to add a dialog to the page
    """

    def __init__(
        self,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
        intentHandler: typing.Optional[Intent] = None,
        hasFloatingActionBtn: bool = False,
        hasAppBar: bool = False,
        pageDialogController: typing.Optional[
            Callable[[any, AlertDialogControls], None]
        ] = None,
        verticalAlignmentInParent=START_ALIGNMENT,
        horizontalAlignmentInParent=START_ALIGNMENT,
        keepBackStack=False,
        onNavigateBack: typing.Optional[Callable] = None,
        showSnackCallback: typing.Optional[Callable[[str, bool], None]] = None,
    ):
        super().__init__()
        self.hasFloatingActionBtn = hasFloatingActionBtn
        self.hasAppBar = hasAppBar
        self.changeRoute = onChangeRouteCallback
        self.intentHandler = intentHandler
        self.pageDialogController = pageDialogController
        self.verticalAlignmentInParent = verticalAlignmentInParent
        self.horizontalAlignmentInParent = horizontalAlignmentInParent
        self.keepBackStack = keepBackStack
        self.onNavigateBack = onNavigateBack
        # callback that shows a snack message which can be an error
        self.showSnack = showSnackCallback

    def get_floating_action_btn_if_any(self):
        """Returns a floating action button OR None"""
        return None

    def get_app_bar_if_any(self):
        """Returns an app bar OR None"""
        return None


class DialogHandler(ABC):
    """Used by views to set, open, and dismiss dialogs"""

    def __init__(
        self,
        dialog: AlertDialog,
        dialogController: Callable[[any, AlertDialogControls], None],
    ):
        super().__init__()
        self.dialogController = dialogController
        self.dialog: AlertDialog = dialog

    def close_dialog(self, e: typing.Optional[any] = None):
        self.dialogController(self.dialog, AlertDialogControls.CLOSE)

    def open_dialog(self, e: typing.Optional[any] = None):
        self.dialogController(self.dialog, AlertDialogControls.ADD_AND_OPEN)

    def dimiss_open_dialogs(self):
        if self.dialog and self.dialog.open:
            self.close_dialog()
