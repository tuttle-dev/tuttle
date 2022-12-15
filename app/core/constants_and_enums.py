from enum import Enum


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
