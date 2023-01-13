from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult
from tuttle.model import Address, User


class UserDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the User model in the database"""

    def __init__(self):
        super().__init__()

    def get_user(self) -> IntentResult:
        """Gets a user if exists

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
                log_message=f"Exception raised @UserDataSource.get_user{e.__class__.__name__}",
                exception=e,
            )

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
        """Creates and stores a user with given info

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : User if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            adddress = Address(
                street=street,
                number=street_num,
                postal_code=postal_code,
                city=city,
                country=country,
            )
            user = User(
                name=name,
                subtitle=title,
                email=email,
                phone_number=phone,
                address=adddress,
            )

            self.store(user)

            return IntentResult(
                was_intent_successful=True,
                data=user,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.create_user {e.__class__.__name__}",
                exception=e,
            )

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
        """Updates a user with given info

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : User  if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            address_id = user.address_id if user.address_id is not None else 123
            add = Address(
                id=address_id,
                street=street,
                number=street_num,
                postal_code=postal_code,
                city=city,
                country=country,
            )
            user = User(
                id=user.id,
                name=name,
                subtitle=title,
                email=email,
                phone_number=phone,
                address_id=add.id,
                address=add,
                profile_photo_path=user.profile_photo_path,
            )
            return IntentResult(was_intent_successful=True, data=user)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.update_user {e.__class__.__name__}",
                exception=e,
            )

    def update_user_photo_url(
        self,
        user: User,
        path: str,
    ) -> IntentResult:
        """Updates a user's profile photo path

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : User  if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            user.profile_photo_path = path
            self.store(user)

            return IntentResult(was_intent_successful=True, data=user)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.update_user_photo_url {e.__class__.__name__}",
                exception=e,
            )
