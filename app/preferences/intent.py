from loguru import logger

from flet import Page

from core.abstractions import ClientStorage
from core.intent_result import IntentResult

from .model import Preferences, PreferencesStorageKeys
from typing import Optional


class PreferencesIntent:
    """Handles Preferences intents

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

    def __init__(
        self,
        client_storage: ClientStorage,
        page: Page,
    ):
        self._client_storage = client_storage
        self._page = page

    def get_preferences(self) -> IntentResult:
        preferences = Preferences()
        for item in PreferencesStorageKeys:
            preference_item_result = self.get_preference_by_key(item)
            if not preference_item_result.data:
                continue
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
            elif item.value == PreferencesStorageKeys.language_key.value:
                preferences.language = preference_item_result.data

        return IntentResult(
            was_intent_successful=True,
            data=preferences,
        )

    def save_preferences(self, preferences: Preferences) -> IntentResult:
        try:
            self.set_preference_key_value_pair(
                PreferencesStorageKeys.theme_mode_key, preferences.theme_mode
            )
            self.set_preference_key_value_pair(
                PreferencesStorageKeys.cloud_acc_id_key, preferences.cloud_acc_id
            )
            self.set_preference_key_value_pair(
                PreferencesStorageKeys.cloud_provider_key,
                preferences.cloud_acc_provider,
            )
            self.set_preference_key_value_pair(
                PreferencesStorageKeys.default_currency_key,
                preferences.default_currency,
            )
            self.set_preference_key_value_pair(
                PreferencesStorageKeys.language_key,
                preferences.language,
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

    def get_preference_by_key(
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

    def set_preference_key_value_pair(
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

    def get_preferred_theme(self) -> IntentResult[Optional[str]]:
        """Returns the preferred theme mode as string"""
        result: IntentResult = self.get_preference_by_key(
            preference_key=PreferencesStorageKeys.theme_mode_key
        )
        if not result.was_intent_successful:
            result.error_msg = "Failed to load your preferred theme"
            result.log_message_if_any()
        return result

    def reset_app(self) -> IntentResult:
        """Resets the app to it's default state"""
        try:
            logger.info("Resetting the app to default state")
            logger.info("Clearing all preferences")
            self._client_storage.clear_preferences()
            logger.info("Clearing all data")
            self._page.window_close()

            return IntentResult(
                was_intent_successful=True,
            )
        except Exception as ex:
            result = IntentResult(
                was_intent_successful=False,
                exception=ex,
                error_msg="Failed to reset app",
            )
            result.log_message_if_any()
            return result
