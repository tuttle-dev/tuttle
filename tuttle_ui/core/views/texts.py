"""Defines different text for display used throughout the app"""

from flet import Column, Text, TextField, TextStyle, padding

from res import colors, fonts, spacing
from typing import Callable, Optional
import typing

from .flet_constants import (
    KEYBOARD_TEXT,
    KEYBOARD_MULTILINE,
    START_ALIGNMENT,
    TXT_ALIGN_LEFT,
)


def get_headline_txt(
    txt: str, size: int = fonts.HEADLING_1_SIZE, color: str = colors.PRIMARY_COLOR
):
    """Displays text formatted as a headline"""
    return Text(
        txt,
        font_family=fonts.HEADLINE_FONT,
        weight=fonts.BOLD_FONT,
        size=size,
    )


def get_headline_with_subtitle(
    title: str,
    subtitle: str,
    alignmentInContainer: str = START_ALIGNMENT,
    txtAlignment: str = TXT_ALIGN_LEFT,
    titleSize: int = fonts.SUBTITLE_1_SIZE,
    subtitleSize: int = fonts.SUBTITLE_2_SIZE,
    subtitleColor: Optional[str] = None,
):
    """Displays text formatted as a headline with a subtitle below it"""
    return Column(
        spacing=0,
        horizontal_alignment=alignmentInContainer,
        controls=[
            Text(
                title,
                font_family=fonts.HEADLINE_FONT,
                size=titleSize,
                text_align=txtAlignment,
            ),
            Text(
                subtitle,
                font_family=fonts.HEADLINE_FONT,
                size=subtitleSize,
                text_align=txtAlignment,
                color=subtitleColor,
            ),
        ],
    )


def get_std_txt_field(
    onChangeCallback,
    lbl: str,
    hint: str,
    keyboardType: str = KEYBOARD_TEXT,
    onFocusCallback: typing.Optional[Callable] = None,
):
    """Displays commonly used text field in app forms"""
    txtFieldPad = padding.symmetric(horizontal=spacing.SPACE_XS)

    return TextField(
        label=lbl,
        keyboard_type=keyboardType,
        content_padding=txtFieldPad,
        hint_text=hint,
        hint_style=TextStyle(size=fonts.CAPTION_SIZE),
        focused_border_width=1,
        on_focus=onFocusCallback,
        on_change=onChangeCallback,
        label_style=TextStyle(size=fonts.BODY_2_SIZE),
        error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
    )


def get_std_multiline_field(
    onChangeCallback,
    lbl: str,
    hint: str,
    onFocusCallback: typing.Optional[Callable] = None,
    keyboardType: str = KEYBOARD_MULTILINE,
    minLines: int = 3,
    maxLines: int = 5,
):
    """Displays commonly used textarea field in app forms"""
    txtFieldHintStyle = TextStyle(size=fonts.CAPTION_SIZE)

    return TextField(
        label=lbl,
        keyboard_type=keyboardType,
        hint_text=hint,
        hint_style=txtFieldHintStyle,
        focused_border_width=1,
        min_lines=minLines,
        max_lines=maxLines,
        on_focus=onFocusCallback,
        on_change=onChangeCallback,
        label_style=TextStyle(size=fonts.BODY_2_SIZE),
        error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
    )


def get_error_txt(
    txt: str,
    size: int = fonts.BODY_2_SIZE,
    color: str = colors.ERROR_COLOR,
    show: bool = True,
):
    """Displays text formatted for errors / warnings"""
    return Text(txt, color=color, size=size, visible=show)
