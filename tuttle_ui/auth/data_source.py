from core.abstractions import ClientStorage
from .model import User
from core.models import Address, IntentResult
from faker import Faker

# TODO implement
class UserDataSourceImpl:
    def __init__(self):
        super().__init__()
        self._dummy_user = None

    def get_user(self) -> IntentResult:
        fake = Faker()
        user_name = fake.name()
        user = User(
            id=fake.random_number(digits=5),
            name=user_name,
            subtitle=fake.job(),
            email=f"{user_name.lower().replace(' ', '')}@example.com",
            phone_number=fake.phone_number(),
            address_id=fake.random_number(digits=5),
            address=Address(
                id=fake.random_number(digits=5),
                street=fake.street_name(),
                number=fake.building_number(),
                postal_code=fake.postalcode(),
                city=fake.city(),
                country=fake.country(),
            ),
        )
        self._dummy_user = user
        return IntentResult(was_intent_successful=True, data=self._dummy_user)

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
        add = Address(
            id=123,
            street=street,
            number=street_num,
            postal_code=postal_code,
            city=city,
            country=country,
        )
        user = User(
            id=456,
            name=name,
            subtitle=title,
            email=email,
            phone_number=phone,
            address_id=add.id,
            address=add,
        )
        self._dummy_user = user
        return IntentResult(was_intent_successful=True, data=self._dummy_user)

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
        )
        self._dummy_user = user
        return IntentResult(was_intent_successful=True, data=self._dummy_user)
