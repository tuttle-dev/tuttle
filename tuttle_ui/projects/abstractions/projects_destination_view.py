from typing import Callable
from flet import UserControl
import typing

from core.abstractions.local_cache import LocalCache
from core.abstractions.destination_view import TuttleDestinationView
from projects.intent.project_intents_impl import ProjectIntentImpl


class ProjectDestinationView(TuttleDestinationView, UserControl):
    """Describes the destination screen that displays all projects

    initializes the intent handler
    """

    def __init__(
        self,
        localCacheHandler: LocalCache,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
    ):
        intentHandler = ProjectIntentImpl(cache=localCacheHandler)
        super().__init__(
            intentHandler=intentHandler, onChangeRouteCallback=onChangeRouteCallback
        )
        self.intentHandler = intentHandler
