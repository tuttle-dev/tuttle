from .model import Preferences, PreferencesStorageKeys
from core.abstractions import ClientStorage
from core.intent_result import IntentResult


class PreferencesIntent:
    def __init__(self, client_storage: ClientStorage):
        self.client_storage = client_storage

    def get_preferences(self) -> IntentResult:
        """if successful, returns a Preferences object as data"""
        preferences = Preferences()
        for item in PreferencesStorageKeys:
            preference_item_result = self.get_preference(item)
            if not preference_item_result.was_intent_successful:
                return IntentResult(
                    was_intent_successful=False,
                    data=None,
                    error_msg="Loading preferences failed!",
                    log_message=preference_item_result.log_message,
                )
            if item.value == PreferencesStorageKeys.theme_mode_key.value:
                preferences.theme_mode = preference_item_result.data
            elif item.value == PreferencesStorageKeys.default_currency_key.value:
                preferences.default_currency = preference_item_result.data
            elif item.value == PreferencesStorageKeys.cloud_acc_id_key.value:
                preferences.cloud_acc_id = preference_item_result.data
            elif item.value == PreferencesStorageKeys.cloud_provider_key.value:
                preferences.cloud_acc_provider = preference_item_result.data

        return IntentResult(
            was_intent_successful=True,
            data=preferences,
        )

    def save_preferences(self, preferences: Preferences) -> IntentResult:
        try:
            self.set_preference(
                PreferencesStorageKeys.theme_mode_key, preferences.theme_mode
            )
            self.set_preference(
                PreferencesStorageKeys.cloud_acc_id_key, preferences.cloud_acc_id
            )
            self.set_preference(
                PreferencesStorageKeys.cloud_provider_key,
                preferences.cloud_acc_provider,
            )
            self.set_preference(
                PreferencesStorageKeys.default_currency_key,
                preferences.default_currency,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                data=None,
                error_msg="Failed to save preferences",
                log_message=f"An exception was raised @PreferencesIntent.save_preferences {e.__class__.__name__}",
            )

    def get_preference(self, preference_key: PreferencesStorageKeys) -> IntentResult:
        """Accepts a key for a preference item and returns the stored value if successful."""
        try:
            preference = self.client_storage.get_value(preference_key.value)
            return IntentResult(was_intent_successful=True, data=preference)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                data=None,
                error_msg="Failed to load that preference item",
                log_message=f"Exception was raised @PreferencesIntent.get_preference f{e.__class__.__name__}",
            )

    def set_preference(
        self, preference_key: PreferencesStorageKeys, value: any
    ) -> IntentResult:
        """Accepts a key-value pair for a preference item and stores the value"""
        try:
            self.client_storage.set_value(
                key=preference_key.value,
                value=value,
            )
            return IntentResult(was_intent_successful=True, data=None)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                data=None,
                error_msg="Saving preferences failed!",
                log_message=f"Exception was raised @PreferencesIntent.set_preference f{e.__class__.__name__}",
            )
