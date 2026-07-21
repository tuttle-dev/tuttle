"""Demo data lifecycle — install and reset."""

from ...app_db import AppDatabase
from ..core.intent_result import IntentResult
from ..core.rpc_utils import reset_all
from ..preferences.model import DEFAULT_INVOICE_TEMPLATE, PreferencesStorageKeys
from ..users.intent import UsersIntent


class DemoIntent:
    def install(self) -> IntentResult:
        users = UsersIntent()
        result = users.ensure_demo()
        if result.was_intent_successful and result.data:
            db_file = getattr(result.data, "db_file", "harry-tuttle.db")
            users.switch(db_file=db_file)
        return result

    def reset(self) -> IntentResult:
        app_db = AppDatabase()
        lang = app_db.get_setting(PreferencesStorageKeys.language_key.value) or "en"
        tmpl = app_db.get_setting(PreferencesStorageKeys.invoice_template_key.value) or DEFAULT_INVOICE_TEMPLATE
        app_db.remove_user("harry-tuttle.db")
        reset_all()

        users = UsersIntent()
        users.ensure_demo(invoice_language=lang, invoice_template=tmpl)
        users.switch(db_file="harry-tuttle.db")

        reg = app_db.get_user_by_db_file("harry-tuttle.db")
        return IntentResult(was_intent_successful=True, data=reg)
