"""App-level key/value settings backed by AppDatabase."""

from ..core.intent_result import IntentResult
from ...app_db import AppDatabase
from ...fx import fx_haircut, primary_currency, supported_currencies


class SettingsIntent:
    def __init__(self):
        self._app_db = AppDatabase()

    # -- Currency conversion ------------------------------------------------

    def get_currency(self, country: str | None = None) -> IntentResult:
        """Currency-conversion settings.

        The primary currency defaults to the active user's operating country
        (only used until they save an explicit ``currency.primary``); callers
        may still pass ``country`` to override.
        """
        return IntentResult(
            was_intent_successful=True,
            data={
                "primary": primary_currency(country or self._active_operating_country()),
                "fx_haircut": str(fx_haircut()),
                "supported": list(supported_currencies()),
            },
        )

    def _active_operating_country(self) -> str:
        from ..auth.data_source import UserDataSource

        try:
            return UserDataSource().get_user().operating_country or "Germany"
        except Exception:
            return "Germany"

    def save_currency(self, primary: str, fx_haircut: str) -> IntentResult:
        self._app_db.set_setting("currency.primary", primary)
        self._app_db.set_setting("currency.fx_haircut", str(fx_haircut))
        return IntentResult(was_intent_successful=True, data=None)

    def get(self, key: str) -> IntentResult:
        return IntentResult(
            was_intent_successful=True,
            data=self._app_db.get_setting(key),
        )

    def set(self, key: str, value: str) -> IntentResult:
        self._app_db.set_setting(key, value)
        return IntentResult(was_intent_successful=True, data=None)

    def get_all(self, prefix: str = None) -> IntentResult:
        return IntentResult(
            was_intent_successful=True,
            data=self._app_db.get_all_settings(prefix=prefix),
        )
