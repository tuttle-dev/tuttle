from .data_source import UserDataSource
from core.intent_result import IntentResult
from typing import Type, Union
from tuttle.model import User


class AuthIntent:
    """Handles User C_R_U_D intents"""

    def __init__(self):
        self._data_source = UserDataSource()

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
    ) -> IntentResult[Union[Type[User], None]]:
        """
        Creates a user with the given details.
        Returns an IntentResult object with the status of the intent and other details

        Parameters
        ----------
        title : str
            Title of the user
        name : str
            Name of the user
        email : str
            Email of the user
        phone : str
            Phone number of the user
        street : str
            Street address of the user
        street_num : str
            Street number of the user
        postal_code : str
            Postal code of the user
        city : str
            City of the user
        country : str
            Country of the user

        Returns
        -------
        IntentResult
            Result object with the status of the intent and other details
        """
        result = self._data_source.create_user(
            title, name, email, phone, street, street_num, postal_code, city, country
        )

        if not result.was_intent_successful:
            result.error_msg = "Login failed! Please check the info and re-try"
            result.log_message_if_any()
        return result

    def get_user_if_exists(self) -> IntentResult[Union[Type[User], None]]:
        """
        Fetches the current user if it exists.
        Returns an IntentResult object with the status of the intent and other details

        Returns
        -------
        IntentResult
            Result object with the status of the intent and other details
        """
        result = self._data_source.get_user()
        if not result.was_intent_successful:
            result.error_msg = "Checking auth status failed! Please restart the app"
            result.log_message_if_any()
        return result

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
    ) -> IntentResult[Union[Type[User], None]]:
        result = self._data_source.update_user(
            user,
            title,
            name,
            email,
            phone,
            street,
            street_num,
            postal_code,
            city,
            country,
        )
        """
        Updates the user with the given details.
        Returns an IntentResult object with the status of the intent and other details

        Parameters
        ----------
        user: User
            instance of user to update
        title : str
            Title of the user
        name : str
            Name of the user
        email : str
            Email of the user
        phone : str
            Phone number of the user
        street : str
            Street address of the user
        street_num : str
            Street number of the user
        postal_code : str
            Postal code of the user
        city : str
            City of the user
        country : str
            Country of the user

        Returns
        -------
        IntentResult
            Result object with the status of the intent and other details
        """
        if not result.was_intent_successful:
            result.error_msg = "Failed to update your info! Please retry"
            result.log_message_if_any()
        return result

    def update_user_photo_path(
        self,
        user: User,
        photo_path,
    ) -> IntentResult[Union[Type[User], None]]:
        """
        Updates the photo path of the user.
        Returns an IntentResult object with the status of the intent and other details

        Parameters
        ----------
        user: User
            instance of user to update
        photo_path : str
            path of the photo

        Returns
        -------
        IntentResult
            Result object with the status of the intent and other details
        """
        result = self._data_source.update_user_photo_path(
            user,
            photo_path,
        )
        if not result.was_intent_successful:
            result.error_msg = "Setting profile photo failed. Please re-try"
            result.log_message_if_any()
        return result
