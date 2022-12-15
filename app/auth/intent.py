from .data_source import UserDataSourceImpl
from core.abstractions import ClientStorage
from core.models import IntentResult
from .model import User


class AuthIntentImpl:
    def __init__(self, local_storage: ClientStorage):
        self.data_source = UserDataSourceImpl()
        self.local_storage = local_storage

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
        return self.data_source.create_user(
            title, name, email, phone, street, street_num, postal_code, city, country
        )

    def get_user(self) -> IntentResult:
        return self.data_source.get_user()

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
        return self.data_source.update_user(
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

    # to delete -  just test on boarding
    def get_user_test_login(self) -> IntentResult:
        # returns no data
        return IntentResult(was_intent_successful=True, data=None)
