"""Preferences backed by the app-level database.

Replaces the legacy ClientStorage-based implementation.  Both the
RPC-facing methods (``get`` / ``save``) and the internal API used by
other intents (``get_preference_by_key``, ``get_preferred_invoice_template``)
read from the same ``AppDatabase`` backend.
"""

from ...app_db import AppDatabase
from ..core.intent_result import IntentResult
from .model import (
    DEFAULT_E_INVOICE_PROFILE,
    DEFAULT_INCLUDE_DUE_DATE,
    DEFAULT_INCLUDE_LOGO,
    DEFAULT_INCLUDE_SIGNATURE,
    DEFAULT_INVOICE_NUMBER_SCHEME,
    DEFAULT_INVOICE_TEMPLATE,
    DEFAULT_THEME_MODE,
    PreferencesStorageKeys,
)


class PreferencesIntent:
    def __init__(self, client_storage=None):
        self._app_db = AppDatabase()

    # -- RPC-facing ------------------------------------------------------------

    def get(self) -> IntentResult:
        raw_include_logo = self._app_db.get_setting(
            PreferencesStorageKeys.include_logo_key.value,
        )
        if raw_include_logo is None:
            include_logo = DEFAULT_INCLUDE_LOGO
        else:
            include_logo = raw_include_logo == "true"

        raw_include_due_date = self._app_db.get_setting(
            PreferencesStorageKeys.include_due_date_key.value,
        )
        if raw_include_due_date is None:
            include_due_date = DEFAULT_INCLUDE_DUE_DATE
        else:
            include_due_date = raw_include_due_date == "true"

        raw_include_signature = self._app_db.get_setting(
            PreferencesStorageKeys.include_signature_key.value,
        )
        if raw_include_signature is None:
            include_signature = DEFAULT_INCLUDE_SIGNATURE
        else:
            include_signature = raw_include_signature == "true"

        return IntentResult(
            was_intent_successful=True,
            data={
                "theme_mode": self._app_db.get_setting(
                    PreferencesStorageKeys.theme_mode_key.value,
                )
                or DEFAULT_THEME_MODE,
                "invoice_template": self._app_db.get_setting(
                    PreferencesStorageKeys.invoice_template_key.value,
                )
                or DEFAULT_INVOICE_TEMPLATE,
                "language": self._app_db.get_setting(
                    PreferencesStorageKeys.language_key.value,
                )
                or "en",
                "invoice_number_scheme": self._app_db.get_setting(
                    PreferencesStorageKeys.invoice_number_scheme_key.value,
                )
                or DEFAULT_INVOICE_NUMBER_SCHEME,
                "e_invoice_profile": self._app_db.get_setting(
                    PreferencesStorageKeys.e_invoice_profile_key.value,
                )
                or DEFAULT_E_INVOICE_PROFILE,
                "include_logo": include_logo,
                "include_due_date": include_due_date,
                "include_signature": include_signature,
            },
        )

    def save(
        self,
        theme_mode=None,
        invoice_template=None,
        language=None,
        invoice_number_scheme=None,
        e_invoice_profile=None,
        include_logo=None,
        include_due_date=None,
        include_signature=None,
    ) -> IntentResult:
        if theme_mode is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.theme_mode_key.value,
                theme_mode,
            )
        if invoice_template is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.invoice_template_key.value,
                invoice_template,
            )
        if language is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.language_key.value,
                language,
            )
        if invoice_number_scheme is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.invoice_number_scheme_key.value,
                invoice_number_scheme,
            )
        if e_invoice_profile is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.e_invoice_profile_key.value,
                e_invoice_profile,
            )
        if include_logo is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.include_logo_key.value,
                "true" if include_logo else "false",
            )
        if include_due_date is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.include_due_date_key.value,
                "true" if include_due_date else "false",
            )
        if include_signature is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.include_signature_key.value,
                "true" if include_signature else "false",
            )
        return IntentResult(was_intent_successful=True, data=None)

    # -- Internal API (used by other intents) ----------------------------------

    def get_preference_by_key(self, key) -> IntentResult:
        k = key.value if hasattr(key, "value") else key
        return IntentResult(
            was_intent_successful=True,
            data=self._app_db.get_setting(k),
        )

    def get_preferred_invoice_template(self) -> IntentResult:
        tmpl = (
            self._app_db.get_setting(
                PreferencesStorageKeys.invoice_template_key.value,
            )
            or DEFAULT_INVOICE_TEMPLATE
        )
        return IntentResult(was_intent_successful=True, data=tmpl)

    def get_include_logo(self) -> IntentResult:
        raw = self._app_db.get_setting(
            PreferencesStorageKeys.include_logo_key.value,
        )
        if raw is None:
            include = DEFAULT_INCLUDE_LOGO
        else:
            include = raw == "true"
        return IntentResult(was_intent_successful=True, data=include)

    def get_include_due_date(self) -> IntentResult:
        raw = self._app_db.get_setting(
            PreferencesStorageKeys.include_due_date_key.value,
        )
        if raw is None:
            include = DEFAULT_INCLUDE_DUE_DATE
        else:
            include = raw == "true"
        return IntentResult(was_intent_successful=True, data=include)

    def get_include_signature(self) -> IntentResult:
        raw = self._app_db.get_setting(
            PreferencesStorageKeys.include_signature_key.value,
        )
        if raw is None:
            include = DEFAULT_INCLUDE_SIGNATURE
        else:
            include = raw == "true"
        return IntentResult(was_intent_successful=True, data=include)
