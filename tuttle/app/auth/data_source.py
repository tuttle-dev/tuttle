from typing import Optional, Type, Union

from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult

from tuttle.dev import deprecated
from tuttle.model import User


class UserDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the User model in the database"""

    def __init__(self):
        super().__init__()

    def get_user(self) -> User:
        """Get a user from the database

        Returns:
            User: The user
        """
        return self.query_the_only(User)

    @deprecated
    def get_user_(self) -> IntentResult[Optional[User]]:
        """
        Get a user from the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : User or None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            user = self.query_the_only(User)
            return IntentResult(
                was_intent_successful=True,
                data=user,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.get_user {e.__class__.__name__}",
                exception=e,
            )

    def save_user(
        self,
        user: Type[User],
    ) -> IntentResult[Union[Type[User], None]]:
        """
        Update an existing user in the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : User if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            self.store(user)
            return IntentResult(was_intent_successful=True, data=user)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.update_user {e.__class__.__name__}",
                exception=e,
            )

    def update_user_photo_path(
        self, user: User, photo_path: str
    ) -> IntentResult[Optional[User]]:
        """
        Update the photo path of an user in the database

        Args:
            user (Type[User]): The user object to be updated
            photo_path (str): the new photo path

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : User if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            user.profile_photo_path = photo_path
            self.store(user)
            return IntentResult(was_intent_successful=True, data=user)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.update_user_photo_path {e.__class__.__name__}",
                exception=e,
            )
