from typing import Type, Union
from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult
from tuttle.model import Address, User


class UserDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the User model in the database"""

    def __init__(self):
        super().__init__()

    def get_user(self) -> IntentResult[Union[Type[User], None]]:
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
    ) -> IntentResult[Type[User]]:
        """
        Create a new user and store it in the database

        Args:
            title (str): title of the user
            name (str): name of the user
            email (str): email of the user
            phone (str): phone number of the user
            street (str): street of the user's address
            street_num (str): street number of the user's address
            postal_code (str): postal code of the user's address
            city (str): city of the user's address
            country (str): country of the user's address

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : User if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            address = Address(
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
                address=address,
            )

            self.store(user)

            return IntentResult(
                was_intent_successful=True,
                data=user,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.create_user{e.__class__.__name__}",
                exception=e,
            )

    def update_user(
        self,
        user: Type[User],
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        street_num: str,
        postal_code: str,
        city: str,
        country: str,
    ) -> IntentResult[Type[User]]:
        """
        Update an existing user in the database

        Args:
            user (Type[User]): The user object to be updated
            title (str): title of the user
            name (str): name of the user
            email (str): email of the user
            phone (str): phone number of the user
            street (str): street of the user's address
            street_num (str): street number of the user's address
            postal_code (str): postal code of the user's address
            city (str): city of the user's address
            country (str): country of the user's address

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : User if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            address = user.address
            address.street = street
            address.number = street_num
            address.postal_code = postal_code
            address.city = city
            address.country = country

            user.name = name
            user.subtitle = title
            user.email = email
            user.phone_number = phone
            user.address = address
            user.profile_photo_path = user.profile_photo_path

            self.store(user)
            return IntentResult(was_intent_successful=True, data=user)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.update_user {e.__class__.__name__}",
                exception=e,
            )

    def update_user_photo_path(
        self, user: Type[User], photo_path: str
    ) -> IntentResult[Type[User]]:
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
