from .abstractions import PreferencesIntent
from .utils import PreferencesIntentsResult
from .preferences_datasource_impl import PreferencesDataSourceImpl
from .preferences_model import Preferences
from core.abstractions import LocalCache


class PreferencesIntentImpl(PreferencesIntent):
    def __init__(self, cache: LocalCache):
        dataSource = PreferencesDataSourceImpl()
        super().__init__(dataSource, cache)

    def get_preferences(self) -> PreferencesIntentsResult:
        return self.dataSource.get_preferences()

    def set_preferences(self, preferences: Preferences) -> PreferencesIntentsResult:
        return self.dataSource.set_preferences(preferences)
