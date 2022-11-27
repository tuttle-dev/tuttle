import typing
from abc import abstractmethod

from core.abstractions import DataSource
from core.abstractions import TuttleDestinationView
from core.abstractions import Intent
from core.abstractions import LocalCache


from .utils import PreferencesIntentsResult
from .preferences_model import Preferences


class PreferencesDataSource(DataSource):
    """Defines methods for manipulating the preferences model"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_preferences(self) -> PreferencesIntentsResult:
        """if successful, returns the current preferences as data"""
        pass

    @abstractmethod
    def set_preferences(self, preferences: Preferences) -> PreferencesIntentsResult:
        """if successful, saves user preferences and returns the preferences as data"""
        pass


class PreferencesIntent(Intent):
    """Handles preferences views intents"""

    def __init__(self, dataSource: PreferencesDataSource, cache: LocalCache):
        super().__init__(cache=cache, dataSource=dataSource)
        self.cache = cache
        self.dataSource = dataSource

    @abstractmethod
    def get_preferences(self) -> PreferencesIntentsResult:
        """if successful, returns the current preferences as data"""
        pass

    @abstractmethod
    def set_preferences(self, preferences: Preferences) -> PreferencesIntentsResult:
        """if successful, saves user preferences and returns the preferences as data"""
        pass
