"""Defines different text fields used throughout the app"""

from flet import TextField, TextStyle, padding


from res import colors, fonts, spacing
from core.ui.utils.flet_constants import KEYBOARD_MULTILINE


def get_std_txt_field(
    onFocusCallback, onChangeCallback, lbl: str, hint: str, keyboardType: str
):
    """Displays commonly used text field in app forms"""
    txtFieldPad = padding.symmetric(horizontal=spacing.SPACE_XS)
    txtFieldHintStyle = TextStyle(color=colors.GRAY_COLOR, size=fonts.CAPTION_SIZE)

    return TextField(
        label=lbl,
        keyboard_type=keyboardType,
        content_padding=txtFieldPad,
        hint_text=hint,
        hint_style=txtFieldHintStyle,
        border_color=colors.GRAY_COLOR,
        focused_border_color=colors.PRIMARY_LIGHT_COLOR,
        focused_border_width=1,
        on_focus=onFocusCallback,
        on_change=onChangeCallback,
    )


def get_std_multiline_field(
    onFocusCallback,
    onChangeCallback,
    lbl: str,
    hint: str,
    keyboardType: str = KEYBOARD_MULTILINE,
    minLines: int = 3,
    maxLines: int = 5,
):
    """Displays commonly used textarea field in app forms"""
    txtFieldHintStyle = TextStyle(color=colors.GRAY_COLOR, size=fonts.CAPTION_SIZE)

    return TextField(
        label=lbl,
        keyboard_type=keyboardType,
        hint_text=hint,
        hint_style=txtFieldHintStyle,
        border_color=colors.GRAY_COLOR,
        focused_border_color=colors.PRIMARY_LIGHT_COLOR,
        focused_border_width=1,
        min_lines=minLines,
        max_lines=maxLines,
        on_focus=onFocusCallback,
        on_change=onChangeCallback,
    )
