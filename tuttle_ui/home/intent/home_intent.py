from core.abstractions.intent import Intent
from authentication.abstractions.auth_intents_result import AuthIntentsResult
from abc import abstractmethod
from authentication.abstractions.user_dataSource import UserDataSource
from core.abstractions.local_cache import LocalCache


class HomeIntent(Intent):
    """Handles user authentication intents"""

    def __init__(self, dataSource: UserDataSource, cache: LocalCache):
        super().__init__(cache=cache, dataSource=dataSource)
        self.cache = cache
        self.dataSource = dataSource

    @abstractmethod
    def is_user_created(
        self,
    ) -> AuthIntentsResult:
        """checks if a user has already been created"""
        pass

    @abstractmethod
    def create_user(
        self, title: str, name: str, email: str, phone: str, address: str
    ) -> AuthIntentsResult:
        """Receives user info and attempts to create a new user"""
        pass
