from core.abstractions import ClientStorage
from core.models import IntentResult
from abc import ABC, abstractmethod
from .user_model import User


class UserDataSource(ABC):
    """Defines methods for instantiating, updating, saving and deleting the user"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def create_user(
        self,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        street_num: str,
        postal_code: str,
        city: str,
        country: str,
    ) -> IntentResult:
        """attempts to create and save a user

        returns data as user_id if created
        else was_intent_successful is False"""
        pass

    @abstractmethod
    def get_user(self) -> IntentResult:
        """If successful, gets the currently signed in user or None as data"""
        pass

    def update_user(
        self,
        user: User,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        street_num: str,
        postal_code: str,
        city: str,
        country: str,
    ) -> IntentResult:
        """Updates the user info

        if successful, returns the updated user
        """
        pass


class AuthIntent(ABC):
    """Handles user user intents"""

    def __init__(self, data_source: UserDataSource, local_storage: ClientStorage):
        self.local_storage = local_storage
        self.data_source = data_source

    @abstractmethod
    def create_user(
        self,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        street_num: str,
        postal_code: str,
        city: str,
        country: str,
    ) -> IntentResult:
        """attempts to create and save a user

        returns data as user_id if created
        else was_intent_successful is False"""
        pass

    @abstractmethod
    def get_user(self) -> IntentResult:
        """If successful, gets the currently signed in user or None as data"""
        pass

    def update_user(
        self,
        user: User,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        street_num: str,
        postal_code: str,
        city: str,
        country: str,
    ) -> IntentResult:
        """Updates the user info

        if successful, returns the updated user
        """
        pass
