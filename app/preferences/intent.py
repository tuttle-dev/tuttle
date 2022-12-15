from .model import Preferences, PreferencesStorageKeys
from core.abstractions import ClientStorage
from core.models import IntentResult
from res.theme import THEME_MODES, get_theme_mode_from_value


class PreferencesIntentImpl:
    def __init__(self, client_storage: ClientStorage):
        self.client_storage = client_storage

    def get_preferences(self) -> IntentResult:
        """if successful, returns a Preferences object as data"""
        theme_mode_value = self.client_storage.get_value(
            key=PreferencesStorageKeys.theme_mode_key.value
        )
        if theme_mode_value is None:
            theme_mode = THEME_MODES.system
        else:
            theme_mode_value = get_theme_mode_from_value(theme_mode_value)
        return IntentResult(
            was_intent_successful=True, data=Preferences(theme_mode=theme_mode)
        )

    def set_preferences(self, preferences: Preferences) -> IntentResult:
        """saves preferences as key value pairs"""
        self.client_storage.set_value(
            key=PreferencesStorageKeys.theme_mode_key.value,
            value=preferences.theme_mode.value,
        )
        return IntentResult(was_intent_successful=True, data=None)
