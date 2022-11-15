from core.abstractions.model import Model
from authentication.utils.auth_intents_result import AuthIntentsResult

class UserModel(Model):
    def __init__(self):
        super().__init__()

    def get_user_if_available():
        result = AuthIntentsResult(wasIntentSuccessful=True,)
        return result # TODO implement

    def create_and_save_user(self, title :str, name : str, email : str, phone : str, address : str):
        result = AuthIntentsResult(wasIntentSuccessful=True,)
        return result #TODO implement