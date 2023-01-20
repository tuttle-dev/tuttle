from core.abstractions import ClientStorage, IntentResult
from preferences.intent import PreferencesIntent
from preferences.model import PreferencesStorageKeys
from typing import Optional


class HomeIntent:
    def __init__(self, local_storage: ClientStorage):
        super().__init__()
        self.preferences_intent = PreferencesIntent(client_storage=local_storage)

    def get_preferred_theme(self) -> IntentResult[Optional[str]]:
        result: IntentResult = self.preferences_intent.get_preference_by_key(
            preference_key=PreferencesStorageKeys.theme_mode_key
        )
        if not result.was_intent_successful:
            result.error_msg = "Failed to load your preferred theme"
            result.log_message_if_any()
        return result
