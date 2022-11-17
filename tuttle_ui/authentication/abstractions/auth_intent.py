from core.abstractions.intent import Intent
from authentication.abstractions.auth_intents_result import AuthIntentsResult
from abc import abstractmethod
from authentication.abstractions.user_model import UserModel
from core.abstractions.local_cache import LocalCache

class AuthIntent(Intent):
    """Handles user authentication intents"""
    def __init__(self, model : UserModel, cache : LocalCache):
        super().__init__(cache=cache, model=model)
        self.cache=cache
        self.model=model

    @abstractmethod
    def is_user_created(self,) -> bool:
        """checks if a user has already been created"""
        pass
        
    @abstractmethod
    def create_user(self, title :str, name : str, email : str, phone : str, address : str) -> AuthIntentsResult:
        """Receives user info and attempts to create a new user"""
        pass