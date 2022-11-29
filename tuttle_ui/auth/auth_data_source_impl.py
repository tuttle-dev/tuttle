from .abstractions import UserDataSource
from core.abstractions import ClientStorage
from .user_model import User
from core.models import Address, IntentResult

# TODO implement
class UserDataSourceImpl(UserDataSource):
    def __init__(self):
        super().__init__()
        self._dummy_user = None

    def get_user(self) -> IntentResult:
        add = Address(
            id=123,
            street="virtual",
            number="164",
            postal_code="34100",
            city="ganzhou",
            country="china",
        )
        user = User(
            id=456,
            name="vlad",
            subtitle="freelancer",
            email="vlad.edna@gmail.com",
            phone_number="123000123",
            address_id=add.id,
            address=add,
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
