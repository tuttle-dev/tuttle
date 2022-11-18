from authentication.abstractions.user_data_source import UserDataSource
from authentication.abstractions.auth_intents_result import AuthIntentsResult

# TODO implement
class UserDataSourceImpl(UserDataSource):
    def __init__(self):
        super().__init__()

    def get_user_id():
        result = AuthIntentsResult(wasIntentSuccessful=True, data=False)
        return result

    def create_and_save_user(
        self, title: str, name: str, email: str, phone: str, address: str
    ):
        result = AuthIntentsResult(wasIntentSuccessful=True, data="userId")
        return result
