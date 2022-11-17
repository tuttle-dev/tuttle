from authentication.abstractions.auth_intent import AuthIntent
from core.abstractions.local_cache import LocalCache
from authentication.model.user_model_impl import UserModelImpl
from authentication.abstractions.auth_intents_result import AuthIntentsResult

from authentication.utils.auth_data_keys import USER_ID, USER_NAME

class AuthIntentImpl(AuthIntent):
    def __init__(self, cache : LocalCache):
        super().__init__(cache=cache, model=UserModelImpl())

    def is_user_created(self,) -> bool:
        userId = self.cache.get_value(USER_ID)
        if userId:
            return True
        return False
        
    def create_user(self, title :str, name : str, email : str, phone : str, address : str) -> AuthIntentsResult:
        result =  self.model.create_and_save_user(title=title, name=name,email=email,phone=phone, address=address)
        if result.wasIntentSuccessful:
            self.cache.set_value(USER_ID, result.data)
        return result