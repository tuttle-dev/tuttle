from .abstractions import PreferencesDataSource
from .utils import PreferencesIntentsResult
from .preferences_model import Preferences

# TODO implement
class PreferencesDataSourceImpl(PreferencesDataSource):
    def __init__(self):
        super().__init__()

    def get_preferences(self) -> PreferencesIntentsResult:
        return PreferencesIntentsResult(wasIntentSuccessful=True, data=Preferences())

    def set_preferences(self, preferences: Preferences) -> PreferencesIntentsResult:
        return PreferencesIntentsResult(wasIntentSuccessful=True, data=preferences)
