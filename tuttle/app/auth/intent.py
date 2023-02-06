from typing import Type, Union, Optional

from core.intent_result import IntentResult
from core.abstractions import Intent

from tuttle.model import User, Address

from .data_source import UserDataSource


class AuthIntent(Intent):
    """Handles User intents"""

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
        website: str,
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
        website : str
            "URL of the user's website."

        Returns
        -------
        IntentResult
            Result object with the status of the intent and other details
        """
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
            VAT_number="",
            website=website,
        )
        result = self._data_source.save_user(user)

        if not result.was_intent_successful:
            result.error_msg = "Login failed! Please check the info and re-try"
            result.log_message_if_any()
        return result

    def get_user_if_exists(self) -> IntentResult[Optional[User]]:
        """
        Fetches the current user if it exists.
        Returns an IntentResult object with the status of the intent and other details

        Returns
        -------
        IntentResult
            Result object with the status of the intent and other details
        """
        result = self._data_source.get_user_()
        if not result.was_intent_successful:
            result.error_msg = "No user data found."
            result.log_message_if_any()
        return result

    def update_user(self, user: User) -> IntentResult[User]:
        """stores the user in the data source"""
        result: IntentResult = self._data_source.save_user(user)
        if not result.was_intent_successful:
            # get old user
            old_user_result: IntentResult = self.get_user_if_exists()
            if old_user_result.was_intent_successful:
                result.data = old_user_result.data
            result.error_msg = "Saving changes failed!"
            result.log_message_if_any()
        return result

    def update_user_with_info(
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
        website: str,
    ) -> IntentResult[Optional[User]]:
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
        website : str
            "URL of the user's website."
        Returns
        -------
        IntentResult
            Result object with the status of the intent and other details
        """
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
        user.website = website
        user.profile_photo_path = user.profile_photo_path
        result = self._data_source.save_user(user)

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
