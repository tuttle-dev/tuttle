from dataclasses import dataclass
from enum import Enum


@dataclass
class Preferences:
    theme_mode: str = ""
    default_currency: str = ""
    language: str = ""


class PreferencesStorageKeys(Enum):
    """defines the keys used in storing preferences as key-value pairs"""

    theme_mode_key = "preferred_theme_mode"
    default_currency_key = "preferred_default_currency"
    language_key = "preferred_language"

    def __str__(self) -> str:
        return str(self.value)
