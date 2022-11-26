import typing
from abc import abstractmethod
from typing import Callable

from flet import UserControl
from .user_model import User
from core.abstractions import DataSource
from core.abstractions import Intent
from core.abstractions import IntentResult
from core.abstractions import LocalCache
from core.abstractions import TuttleView


class AuthIntentsResult(IntentResult):
    """Wrapper for result object when an intent is executed"""

    def __init__(
        self,
        data=None,
        wasIntentSuccessful: bool = False,
        errorMsgIfAny: str = "",
        logMsg: str = "",
    ):
        super().__init__(
            data=data,
            wasIntentSuccessful=wasIntentSuccessful,
            errorMsgIfAny=errorMsgIfAny,
            logMsg=logMsg,
        )


class UserDataSource(DataSource):
    """Defines methods for instantiating, updating, saving and deleting the user"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_user_id() -> AuthIntentsResult:
        """checks if user has been created,

        returns data as user_id if created else None
        if an error occurs wasIntentSuccessful is False"""
        pass

    @abstractmethod
    def create_and_save_user(
        self,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        streetNum: str,
        postalCode: str,
        city: str,
        country: str,
    ) -> AuthIntentsResult:
        """attempts to create and save a user

        returns data as user_id if created
        else wasIntentSuccessful is False"""
        pass

    @abstractmethod
    def get_user_profile(self) -> AuthIntentsResult:
        """If successful and signed in, gets the currently signed in user as data"""
        pass

    def update_user(
        self,
        user: User,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        streetNum: str,
        postalCode: str,
        city: str,
        country: str,
    ) -> AuthIntentsResult:
        """Updates the user info

        if successful, returns the updated user
        """
        pass


class AuthIntent(Intent):
    """Handles user user intents"""

    def __init__(self, dataSource: UserDataSource, cache: LocalCache):
        super().__init__(cache=cache, dataSource=dataSource)
        self.cache = cache
        self.dataSource = dataSource

    @abstractmethod
    def is_user_created(
        self,
    ) -> bool:
        """checks if a user has already been created"""
        pass

    @abstractmethod
    def create_user(
        self,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        streetNum: str,
        postalCode: str,
        city: str,
        country: str,
    ) -> AuthIntentsResult:
        """Receives user info and attempts to create a new user"""
        pass

    @abstractmethod
    def get_user_profile(self) -> AuthIntentsResult:
        """If successful and signed in, gets the currently signed in user as data"""
        pass

    @abstractmethod
    def cache_user_data(self, key: str, data: any):
        """Caches frequently used user related info as key-value pairs"""
        pass

    def update_user(
        self,
        user: User,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        streetNum: str,
        postalCode: str,
        city: str,
        country: str,
    ) -> AuthIntentsResult:
        """Updates the user info

        if successful, returns the updated user
        """
        pass


class AuthView(TuttleView, UserControl):
    """User creation screen

    If the user is authenticated,
    re-route them to home Screen
    else display a login form and a splash section
    """

    def __init__(
        self,
        changeRouteCallback: Callable[[str, typing.Optional[any]], None],
        intentHandler: AuthIntent,
    ):
        super().__init__(
            intentHandler=intentHandler,
            onChangeRouteCallback=changeRouteCallback,
        )
        self.intentHandler = intentHandler
