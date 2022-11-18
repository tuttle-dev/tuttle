from abc import ABC
import typing
from typing import Callable

from res.colors import WHITE_COLOR

from .intent import Intent


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
