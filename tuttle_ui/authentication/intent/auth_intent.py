from core.abstractions.intent import Intent
from core.abstractions.model import Model

from authentication.model.user_model import UserModel
from authentication.utils.auth_intents_result import AuthIntentsResult

class AuthIntent(Intent):
    """Handles user authentication intents"""
    def __init__(self,):
        super().__init__()
        self.set_model(model=UserModel())

    def set_model(self, model: UserModel):
        self.model = model

    def get_user(self,) -> AuthIntentsResult:
        return self.model.get_user_if_available()
        
    def attempt_login(self, title :str, name : str, email : str, phone : str, address : str) -> AuthIntentsResult:
        return self.model.create_and_save_user(title=title, name=name,email=email,phone=phone, address=address)



