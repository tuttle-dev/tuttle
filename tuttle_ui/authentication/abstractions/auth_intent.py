from core.abstractions.intent import Intent
from authentication.abstractions.auth_intents_result import AuthIntentsResult
from abc import abstractmethod
from authentication.abstractions.user_data_source import UserDataSource
from core.abstractions.local_cache import LocalCache


class AuthIntent(Intent):
    """Handles user authentication intents"""

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
        self, title: str, name: str, email: str, phone: str, address: str
    ) -> AuthIntentsResult:
        """Receives user info and attempts to create a new user"""
        pass

    @abstractmethod
    def cache_user_data(self, key: str, data: any):
        """Caches frequently used user related info as key-value pairs"""
        pass
