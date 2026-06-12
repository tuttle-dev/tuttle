"""Preferences backed by the app-level database.

Replaces the legacy ClientStorage-based implementation.  Both the
RPC-facing methods (``get`` / ``save``) and the internal API used by
other intents (``get_preference_by_key``, ``get_preferred_invoice_template``)
read from the same ``AppDatabase`` backend.
"""

from ..core.intent_result import IntentResult
from ...app_db import AppDatabase
from .model import (
    DEFAULT_E_INVOICE_PROFILE,
    DEFAULT_INCLUDE_LOGO,
    DEFAULT_INVOICE_NUMBER_SCHEME,
    DEFAULT_INVOICE_TEMPLATE,
    PreferencesStorageKeys,
)
import json


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

        show_payment_qr_val = self._app_db.get_setting(
            PreferencesStorageKeys.show_payment_qr_key.value,
        )
        if show_payment_qr_val is None:
            show_payment_qr = True
        else:
            try:
                show_payment_qr = json.loads(show_payment_qr_val)
            except Exception:
                show_payment_qr = show_payment_qr_val == "true"

        return IntentResult(
            was_intent_successful=True,
            data={
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
                "show_payment_qr": show_payment_qr,
            },
        )

    def save(
        self,
        invoice_template=None,
        language=None,
        invoice_number_scheme=None,
        e_invoice_profile=None,
        include_logo=None,
        show_payment_qr=None,
    ) -> IntentResult:
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
        if show_payment_qr is not None:
            self._app_db.set_setting(
                PreferencesStorageKeys.show_payment_qr_key.value,
                show_payment_qr,
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
