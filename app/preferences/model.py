from dataclasses import dataclass
from enum import Enum


@dataclass
class Preferences:
    theme_mode: str = ""
    cloud_acc_id: str = ""
    cloud_acc_provider: str = ""
    default_currency: str = ""
    language: str = ""


class PreferencesStorageKeys(Enum):
    """defines the keys used in storing preferences as key-value pairs"""

    theme_mode_key = "preferred_theme_mode"
    cloud_acc_id_key = "preferred_cloud_acc_id"
    cloud_provider_key = "preferred_cloud_acc_provider"
    default_currency_key = "preferred_default_currency"
    language_key = "preferred_language"

    def __str__(self) -> str:
        return str(self.value)
