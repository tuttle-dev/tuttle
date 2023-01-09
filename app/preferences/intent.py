from .model import Preferences, PreferencesStorageKeys
from core.abstractions import ClientStorage
from core.models import IntentResult
from res.theme import THEME_MODES, get_theme_mode_from_value


class PreferencesIntent:
    def __init__(self, client_storage: ClientStorage):
        self.client_storage = client_storage

    def get_preferences(self) -> IntentResult:
        """if successful, returns a Preferences object as data"""
        preferred_theme = self.client_storage.get_value(
            key=PreferencesStorageKeys.theme_mode_key.value
        )
        if preferred_theme is None:
            preferred_theme = THEME_MODES.system
        else:
            preferred_theme = get_theme_mode_from_value(preferred_theme)

        preferred_icloud_id = self.client_storage.get_value(
            key=PreferencesStorageKeys.icloud_acc_id_key.value
        )
        return IntentResult(
            was_intent_successful=True,
            data=Preferences(
                theme_mode=preferred_theme, icloud_acc_id=preferred_icloud_id
            ),
        )

    def set_preferences(self, preferences: Preferences) -> IntentResult:
        """saves preferences as key value pairs"""
        try:
            self.client_storage.set_value(
                key=PreferencesStorageKeys.theme_mode_key.value,
                value=preferences.theme_mode.value,
            )
            self.client_storage.set_value(
                key=PreferencesStorageKeys.icloud_acc_id_key.value,
                value=preferences.icloud_acc_id,
            )
            return IntentResult(was_intent_successful=True, data=None)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                data=None,
                error_msg_if_err="failed to save your preferences",
                log_message=f"an exception was raised @PreferencesIntent.set_preferences {e}",
            )

    def get_icloud_account(self):
        """if successful, returns user's preferred icloud account as data"""
        try:
            result = self.client_storage.get_value(
                key=PreferencesStorageKeys.icloud_acc_id_key.value
            )
            return IntentResult(was_intent_successful=True, data=result)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                data=None,
                error_msg_if_err="failed to load icloud account",
                log_message=f"an exception was raised @PreferencesIntent.get_icloud_account {e}",
            )

    def set_preferred_icloud_account(self, icloud_acc_id):
        """attempts to store a new preferred_icloud_account"""
        try:
            self.client_storage.set_value(
                key=PreferencesStorageKeys.icloud_acc_id_key.value,
                value=icloud_acc_id,
            )
            return IntentResult(was_intent_successful=True, data=None)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"an exception was raised @Preferences.set_preferred_icloud_accoun",
            )
