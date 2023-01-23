import warnings

warnings.warn(
    "wastebasket module, content will be moved to other modules",
    DeprecationWarning,
    stacklevel=2,
)

from typing import List, Tuple

import base64
from enum import Enum

from flet import icons

import pycountry

from tuttle.dev import deprecated


class AlertDialogControls(Enum):
    """Controls for the page's pop up dialog"""

    ADD_AND_OPEN = 1
    CLOSE = 2


# Layout Alignments
STRETCH_ALIGNMENT = "stretch"
SPACE_BETWEEN_ALIGNMENT = "spaceBetween"
START_ALIGNMENT = "start"
END_ALIGNMENT = "end"
CENTER_ALIGNMENT = "center"


# Fit
CONTAIN = "cover"

# Keyboard types
KEYBOARD_NAME = "name"
KEYBOARD_PHONE = "phone"
KEYBOARD_EMAIL = "email"
KEYBOARD_TEXT = "text"
KEYBOARD_MULTILINE = "multiline"
KEYBOARD_NUMBER = "number"
KEYBOARD_DATETIME = "datetime"
KEYBOARD_URL = "url"
KEYBOARD_PASSWORD = "visiblePassword"
KEYBOARD_ADDRESS = "streetAddress"
KEYBOARD_NONE = "none"

# scrolling
AUTO_SCROLL = "auto"
ADAPTIVE_SCROLL = "adaptive"
HIDDEN_SCROLL = "hidden"
ALWAYS_SCROLL = "always"

# Text Alignment
TXT_ALIGN_RIGHT = "right"
TXT_ALIGN_CENTER = "center"
TXT_ALIGN_JUSTIFY = "justify"
TXT_ALIGN_START = "start"
TXT_ALIGN_END = "end"
TXT_ALIGN_LEFT = "left"

# Navigation rail label style
ALWAYS_SHOW = "all"
NEVER_SHOW = "none"
ONLY_SELECTED = "selected"
# compact rail type (label is none)
COMPACT_RAIL_WIDTH = 56
# rail group_alignment
CENTER_RAIL = 0.0


# Control state
HOVERED = "hovered"
FOCUSED = "focused"
SELECTED = "selected"
PRESSED = "pressed"
OTHER_CONTROL_STATES = ""


@deprecated
def is_empty_str(txt: str) -> bool:
    # TODO: equivalent to txt.strip() == "", so remove function
    return len(txt.strip()) == 0



def truncate_str(txt: str, max_chars: int = 25) -> str:
    if not txt:
        return ""
    if len(txt) <= max_chars:
        return txt
    else:
        return f"{txt[0:max_chars]}..."


def image_to_base64(image_path):
    """Converts an image to a base64-encoded string."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


class TuttleComponentIcons(Enum):
    """ "Defines the icons used for different components throughout the app"""

    dashboard_icon = icons.SPEED
    dashboard_selected_icon = icons.SPEED_ROUNDED
    project_icon = icons.WORK_OUTLINE
    project_selected_icon = icons.WORK_ROUNDED
    contact_icon = icons.CONTACT_MAIL_OUTLINED
    contact_selected_icon = icons.CONTACT_MAIL_ROUNDED
    client_icon = icons.CONTACTS_OUTLINED
    client_selected_icon = icons.CONTACTS_ROUNDED
    contract_icon = icons.HANDSHAKE_OUTLINED
    contract_selected_icon = icons.HANDSHAKE_ROUNDED
    timetracking_icon = icons.TIMER_OUTLINED
    timetracking_selected_icon = icons.TIMER_ROUNDED
    invoicing_icon = icons.RECEIPT_OUTLINED
    invoicing_selected_icon = icons.RECEIPT_ROUNDED
    datatable_icon = icons.TABLE_CHART
    datatable_selected_icon = icons.TABLE_CHART_ROUNDED

    def __str__(self) -> str:
        return str(self.value)


def get_currencies() -> List[Tuple[str, str, str]]:
    """Returns a list of available currencies sorted alphabetically"""
    currencies = []
    currency_list = list(pycountry.currencies)
    for currency in currency_list:
        abbreviation = currency.alpha_3
        symbol = currency.symbol if hasattr(currency, "symbol") else None
        currencies.append((currency.name, abbreviation, symbol))
    # sort alphabetically by abbreviation
    currencies.sort(key=lambda tup: tup[1])
    return currencies
