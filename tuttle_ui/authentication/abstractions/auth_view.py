from typing import Callable
from flet import UserControl
import typing
from authentication.intent.auth_intent_impl import AuthIntentImpl
from core.abstractions.local_cache import LocalCache
from core.abstractions.view import TuttleView


class AuthView(TuttleView, UserControl):
    """Defines the initial Screen Displayed
    
    If the user is authenticated,
    re-route them to home Screen
    else display a login form and a splash section
    """
    def __init__(self, changeRouteCallback:Callable[[str, typing.Optional[any]], None], localCacheHandler : LocalCache):
        intentHandler = AuthIntentImpl(cache=localCacheHandler)
        super().__init__(intentHandler=intentHandler, onChangeRouteCallback=changeRouteCallback)
        self.intentHandler = intentHandler