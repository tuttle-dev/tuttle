from core.abstractions.model import Model
from authentication.abstractions.auth_intents_result import AuthIntentsResult
from abc import abstractmethod


class UserModel(Model):
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
        self, title: str, name: str, email: str, phone: str, address: str
    ) -> AuthIntentsResult:
        """attempts to create and save a user

        returns data as user_id if created
        else wasIntentSuccessful is False"""
        pass
