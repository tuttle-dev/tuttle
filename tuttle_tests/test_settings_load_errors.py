"""Settings that fail to load are an error, not defaults the user could save over the real ones."""

from types import SimpleNamespace

from tuttle.app.auth.data_source import UserDataSource
from tuttle.app.settings.intent import SettingsIntent
from tuttle.app.users.intent import UsersIntent


def _unreadable(self):
    raise RuntimeError("database is locked")


def test_a_profile_that_fails_to_load_is_an_error_not_an_empty_profile(monkeypatch):
    intent = UsersIntent()
    monkeypatch.setattr(intent._app_db, "get_user_by_db_file", lambda f: SimpleNamespace(model_dump=lambda: {"db_file": f}))
    monkeypatch.setattr(UserDataSource, "get_user", _unreadable)

    result = intent.get_active()

    assert not result.was_intent_successful
    assert result.error_msg == "Your profile could not be loaded. Details are in the application log."


def test_currency_settings_that_fail_to_load_are_an_error(monkeypatch):
    monkeypatch.setattr(UserDataSource, "get_user", _unreadable)

    result = SettingsIntent().get_currency()

    assert not result.was_intent_successful
    assert result.error_msg == "The currency settings could not be loaded. Details are in the application log."


def test_a_given_country_needs_no_profile(monkeypatch):
    monkeypatch.setattr(UserDataSource, "get_user", _unreadable)

    assert SettingsIntent().get_currency(country="Germany").data["default"] == "EUR"


def test_no_user_yet_is_not_an_error(monkeypatch):
    monkeypatch.setattr(UserDataSource, "get_user", lambda self: None)

    assert SettingsIntent().get_currency().was_intent_successful
