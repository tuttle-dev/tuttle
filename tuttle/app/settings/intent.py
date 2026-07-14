"""App-level key/value settings backed by AppDatabase."""

from ..core.intent_result import IntentResult
from ...app_db import AppDatabase
from ...fx import SUPPORTED_CURRENCIES, fx_haircut, primary_currency


class SettingsIntent:
    def __init__(self):
        self._app_db = AppDatabase()

    # -- Currency conversion ------------------------------------------------

    def get_currency(self, country: str = "Germany") -> IntentResult:
        """Currency-conversion settings, defaulted from the operating country."""
        return IntentResult(
            was_intent_successful=True,
            data={
                "primary": primary_currency(country),
                "fx_haircut": str(fx_haircut()),
                "supported": list(SUPPORTED_CURRENCIES),
            },
        )

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
