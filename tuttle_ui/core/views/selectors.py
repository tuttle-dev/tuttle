from flet import Dropdown, dropdown, TextStyle, padding, icons
from typing import List, Callable
from res import fonts, spacing, dimens, colors


def get_dropdown(
    lbl: str,
    hint: str,
    onChange: Callable,
    items: List[str],
):
    options = []
    for item in items:
        options.append(
            dropdown.Option(
                text=item,
            )
        )
    return Dropdown(
        label=lbl,
        hint_text=hint,
        options=options,
        text_size=fonts.BODY_1_SIZE,
        label_style=TextStyle(size=fonts.BODY_2_SIZE),
        on_change=onChange,
        content_padding=padding.all(spacing.SPACE_XS),
        error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
    )
