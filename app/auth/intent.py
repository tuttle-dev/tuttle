from .data_source import UserDataSource
from core.abstractions import ClientStorage
from core.models import IntentResult

from tuttle.model import User


class AuthIntent:
    def __init__(self):
        self.data_source = UserDataSource()

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
        result = self.data_source.create_user(
            title, name, email, phone, street, street_num, postal_code, city, country
        )
        if not result.was_intent_successful:
            result.error_msg = "Login failed! Please check the info and re-try"
        return result

    def get_user(self) -> IntentResult:
        result = self.data_source.get_user()
        if not result.was_intent_successful:
            result.error_msg = "Checking auth status failed! Please restart the app"
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
        result = self.data_source.update_user(
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
        return result

    def update_user_photo(
        self,
        user: User,
        upload_url,
    ):
        result = self.data_source.update_user_photo_url(
            user,
            upload_url,
        )
        if not result.was_intent_successful:
            result.error_msg = "Setting profile photo failed. Please re-try"
        return result
