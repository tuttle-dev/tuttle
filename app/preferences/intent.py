from .model import Preferences, PreferencesStorageKeys
from core.abstractions import ClientStorage
from core.intent_result import IntentResult


class PreferencesIntent:
    """Handles Preferences C_R_U_D intents

    Intents handled (Methods)
    ---------------

    get_preferences_intent
        fetching a Preferences object

    save_preferences_intent
        storing a Preferences object

    get_preference_by_key_intent
        reading a single preference value given it's key

    set_preference_key_value_pair_intent
        storing a preference item given it's key and value
    """

    def __init__(self, client_storage: ClientStorage):

        self._client_storage = client_storage

    def get_preferences_intent(self) -> IntentResult:
        preferences = Preferences()
        for item in PreferencesStorageKeys:
            preference_item_result = self.get_preference_by_key_intent(item)
            if not preference_item_result.was_intent_successful:
                preference_item_result.log_message_if_any()
                return IntentResult(
                    was_intent_successful=False,
                    error_msg="Loading preferences failed!",
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

    def save_preferences_intent(self, preferences: Preferences) -> IntentResult:
        try:
            self.set_preference_key_value_pair_intent(
                PreferencesStorageKeys.theme_mode_key, preferences.theme_mode
            )
            self.set_preference_key_value_pair_intent(
                PreferencesStorageKeys.cloud_acc_id_key, preferences.cloud_acc_id
            )
            self.set_preference_key_value_pair_intent(
                PreferencesStorageKeys.cloud_provider_key,
                preferences.cloud_acc_provider,
            )
            self.set_preference_key_value_pair_intent(
                PreferencesStorageKeys.default_currency_key,
                preferences.default_currency,
            )
        except Exception as e:
            result = IntentResult(
                was_intent_successful=False,
                exception=e,
                error_msg="Failed to save preferences",
                log_message=f"An exception was raised @PreferencesIntent.save_preferences {e.__class__.__name__}",
            )
            result.log_message_if_any()
            return result

    def get_preference_by_key_intent(
        self, preference_key: PreferencesStorageKeys
    ) -> IntentResult:
        try:
            preference = self._client_storage.get_value(preference_key.value)
            return IntentResult(was_intent_successful=True, data=preference)
        except Exception as e:
            result = IntentResult(
                was_intent_successful=False,
                exception=e,
                error_msg="Failed to load that preference item",
                log_message=f"Exception was raised @PreferencesIntent.get_preference f{e.__class__.__name__}",
            )
            result.log_message_if_any()
            return result

    def set_preference_key_value_pair_intent(
        self, preference_key: PreferencesStorageKeys, value: any
    ) -> IntentResult:
        try:
            self._client_storage.set_value(
                key=preference_key.value,
                value=value,
            )
            return IntentResult(was_intent_successful=True, data=None)
        except Exception as e:
            result = IntentResult(
                was_intent_successful=False,
                exception=e,
                error_msg="Saving preferences failed!",
                log_message=f"Exception was raised @PreferencesIntent.set_preference f{e.__class__.__name__}",
            )
            result.log_message_if_any()
            return result
