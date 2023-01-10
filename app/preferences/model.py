from dataclasses import dataclass
from enum import Enum


@dataclass
class Preferences:
    theme_mode: str = ""
    icloud_acc_id: str = ""
    default_currency: str = ""


class PreferencesStorageKeys(Enum):
    """defines the keys used in storing preferences as key-value pairs"""

    theme_mode_key = "preferred_theme_mode"
    icloud_acc_id_key = "preferred_icloud_acc_id"
    default_currency_key = "preferred_default_currency"

    def __str__(self) -> str:
        return str(self.value)
