from core.abstractions import ClientStorage, SQLModelDataSourceMixin

from core.models import IntentResult

from tuttle.model import Address, User


class UserDataSource(SQLModelDataSourceMixin):
    def __init__(self):
        super().__init__()
        self._dummy_user = None

    def get_user(self) -> IntentResult:
        """returns data as the user if one exists else None"""
        user = self.query_the_only(User)
        return IntentResult(
            was_intent_successful=True,
            data=user,
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
    ) -> IntentResult:
        """creates and saves a user instance
        returns data as the created user if successful"""
        try:
            adddress = Address(
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
                address=adddress,
            )

            self.store(user)

            return IntentResult(
                was_intent_successful=True,
                data=user,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised at UserDataSource.create_user {e}",
            )

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
        """attempts to update an existing user.
        returns data as the updated user if succesful"""
        try:
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
                profile_photo=user.profile_photo,
            )
            return IntentResult(was_intent_successful=True, data=user)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.update_user {e}",
            )

    def update_user_photo_url(self, url):
        """TODO saves the path of the new uploaded profile photo"""
        try:
            return IntentResult(was_intent_successful=True, data=None)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @UserDataSource.update_user_photo_url {e}",
            )
