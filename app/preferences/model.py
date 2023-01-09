from dataclasses import dataclass
from res.theme import THEME_MODES
from enum import Enum


@dataclass
class Preferences:
    theme_mode: THEME_MODES = THEME_MODES.dark
    icloud_acc_id: str = ""


class PreferencesStorageKeys(Enum):
    """defines the keys used in storing preferences as key-value pairs"""

    theme_mode_key = "preferred_theme_mode"
    icloud_acc_id_key = "preferred_icloud_acc_id"

    def __str__(self) -> str:
        return str(self.value)
