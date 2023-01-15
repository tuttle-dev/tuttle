from .data_source import UserDataSource
from core.intent_result import IntentResult

from tuttle.model import User


class AuthIntent:
    """Handles User C_R_U_D intents

    Intents handled (Methods)
    ---------------

    create_user_intent
        creating the user

    get_user_if_exists_intent
        fetching the current user if exists

    update_user_intent
        updating a user's info

    update_user_photo_path_intent
        updating the photo path attr of the user
    """

    def __init__(self):
        """
        Attributes
        ----------
        _data_source : UserDatasource
            reference to the user's data source
        """
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
    ) -> IntentResult:
        result = self._data_source.create_user(
            title, name, email, phone, street, street_num, postal_code, city, country
        )
        if not result.was_intent_successful:
            result.error_msg = "Login failed! Please check the info and re-try"
            result.log_message_if_any()
        return result

    def get_user_if_exists(self) -> IntentResult:
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
    ) -> IntentResult:
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
        if not result.was_intent_successful:
            result.error_msg = "Failed to update your info! Please retry"
            result.log_message_if_any()
        return result

    def update_user_photo_path(
        self,
        user: User,
        photo_path,
    ) -> IntentResult:
        result = self._data_source.update_user_photo_path(
            user,
            photo_path,
        )
        if not result.was_intent_successful:
            result.error_msg = "Setting profile photo failed. Please re-try"
            result.log_message_if_any()
        return result
