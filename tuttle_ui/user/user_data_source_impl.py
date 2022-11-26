from user.abstractions import UserDataSource
from user.abstractions import AuthIntentsResult
from user.user_model import User
from core.models import Address

# TODO implement
class UserDataSourceImpl(UserDataSource):
    def __init__(self):
        super().__init__()

    def get_user_id():
        result = AuthIntentsResult(wasIntentSuccessful=True, data=False)
        return result

    def create_and_save_user(
        self,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        streetNum: str,
        postalCode: str,
        city: str,
        country: str,
    ) -> AuthIntentsResult:
        result = AuthIntentsResult(wasIntentSuccessful=True, data="userId")
        return result

    def get_user_profile(self) -> AuthIntentsResult:
        result = AuthIntentsResult(
            wasIntentSuccessful=True,
            data=User(
                id=1,
                title="Freelancer",
                email="freelancer@tuttle.com",
                name="vladimir",
                phone="+8617370743331",
                address=None,
            ),
        )
        return result

    def update_user(
        self,
        user: User,
        title: str,
        name: str,
        email: str,
        phone: str,
        street: str,
        streetNum: str,
        postalCode: str,
        city: str,
        country: str,
    ) -> AuthIntentsResult:
        ad = Address(
            id=user.address.id if user.address else 1,
            city=city,
            street=street,
            country=country,
            postal_code=postalCode,
            number=streetNum,
        )
        # todo save address
        user = User(
            id=user.id, title=title, name=name, email=email, phone=phone, address=ad
        )
        return AuthIntentsResult(wasIntentSuccessful=True, data=user)
