from .data_source import UserDataSource
from core.abstractions import ClientStorage
from core.models import IntentResult

from tuttle.model import User


class AuthIntent:
    def __init__(self, local_storage: ClientStorage):
        self.data_source = UserDataSource()
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
