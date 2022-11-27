from dataclasses import dataclass
from res.theme import THEME_MODES


@dataclass
class Preferences:
    theme_mode: THEME_MODES = THEME_MODES.system
