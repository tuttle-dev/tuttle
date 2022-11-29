from dataclasses import dataclass
from res.theme import THEME_MODES
from enum import Enum


@dataclass
class Preferences:
    theme_mode: THEME_MODES = THEME_MODES.system


class PreferencesStorageKeys(Enum):
    """defines the keys used in storing preferences as key-value pairs"""

    theme_mode_key = "preferences_theme_mode"

    def __str__(self) -> str:
        return str(self.value)
