import datetime
import typing
from typing import Callable, List, Optional

from flet import (
    Column,
    Container,
    Dropdown,
    ElevatedButton,
    FilledButton,
    Image,
    ProgressBar,
    Row,
    Text,
    TextField,
    TextStyle,
    UserControl,
    dropdown,
    padding,
)

from res import colors, dimens, fonts, image_paths
from res.strings import APP_NAME, DAY_LBL, MONTH_LBL, YEAR_LBL

from .constants_and_enums import (
    CENTER_ALIGNMENT,
    CONTAIN,
    KEYBOARD_MULTILINE,
    KEYBOARD_TEXT,
    OTHER_CONTROL_STATES,
    SPACE_BETWEEN_ALIGNMENT,
    START_ALIGNMENT,
    TXT_ALIGN_LEFT,
)

stdSpace = Container(
    height=dimens.SPACE_STD, width=dimens.SPACE_STD, padding=0, margin=0
)
mdSpace = Container(height=dimens.SPACE_MD, width=dimens.SPACE_MD, padding=0, margin=0)
smSpace = Container(height=dimens.SPACE_SM, width=dimens.SPACE_SM, padding=0, margin=0)
xsSpace = Container(height=dimens.SPACE_XS, width=dimens.SPACE_XS, padding=0, margin=0)


def get_headline_txt(
    txt: str, size: int = fonts.SUBTITLE_1_SIZE, color: Optional[str] = None
):
    """Displays text formatted as a headline"""
    return Text(
        txt,
        font_family=fonts.HEADLINE_FONT,
        weight=fonts.BOLD_FONT,
        size=size,
        color=color,
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
    on_change,
    lbl: str,
    hint: str = "",
    keyboard_type: str = KEYBOARD_TEXT,
    on_focus: typing.Optional[Callable] = None,
    initial_value: typing.Optional[str] = None,
    expand: typing.Optional[int] = None,
    width: typing.Optional[int] = None,
):
    """Displays commonly used text field in app forms"""
    txtFieldPad = padding.symmetric(horizontal=dimens.SPACE_XS)

    return TextField(
        label=lbl,
        keyboard_type=keyboard_type,
        content_padding=txtFieldPad,
        hint_text=hint,
        hint_style=TextStyle(size=fonts.CAPTION_SIZE),
        value=initial_value,
        focused_border_width=1,
        on_focus=on_focus,
        on_change=on_change,
        expand=expand,
        width=width,
        text_size=fonts.BODY_1_SIZE,
        label_style=TextStyle(size=fonts.BODY_2_SIZE),
        error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
    )


def get_std_multiline_field(
    on_change,
    lbl: str,
    hint: str,
    on_focus: typing.Optional[Callable] = None,
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
        on_focus=on_focus,
        on_change=on_change,
        text_size=fonts.BODY_1_SIZE,
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


def get_body_txt(
    txt: str,
    size: int = fonts.BODY_1_SIZE,
    color: Optional[str] = None,
    show: bool = True,
):
    """Displays text formatted for body"""
    return Text(txt, color=color, size=size, visible=show)


def get_primary_btn(
    on_click,
    label: str,
    width: int = 200,
):
    """An elevated button with primary styling"""
    return FilledButton(label, width=width, on_click=on_click)


def get_secondary_btn(
    on_click,
    label: str,
    width: int = 200,
):
    """An elevated button with secondary styling"""
    return ElevatedButton(
        label,
        width=width,
        on_click=on_click,
    )


def get_image(path: str, semantic_label: str, width: int):
    return Container(
        width=width,
        content=Image(src=path, fit=CONTAIN, semantics_label=semantic_label),
    )


def get_app_logo(width: int = 12):
    """Returns app logo"""
    return Container(
        width=width,
        content=Image(src=image_paths.logoPath, fit=CONTAIN, semantics_label="logo"),
    )


def get_labelled_logo():
    """Returns app logo with app name next to it"""
    return Row(
        vertical_alignment="center",
        controls=[
            get_app_logo(),
            get_headline_txt(
                APP_NAME,
                size=fonts.HEADLINE_3_SIZE,
            ),
        ],
    )


horizontal_progress = ProgressBar(
    width=320,
    height=4,
)


def update_dropdown_items(dropDown: Dropdown, items: List[str]):
    options = []
    for item in items:
        options.append(
            dropdown.Option(
                text=item,
            )
        )
    dropDown.options = options


def get_dropdown(
    lbl: str,
    on_change: Callable,
    items: List[str],
    hint: Optional[str] = "",
    width: Optional[int] = None,
    initial_value: Optional[str] = None,
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
        on_change=on_change,
        width=width,
        value=initial_value,
        content_padding=padding.all(dimens.SPACE_XS),
        error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
    )


class DateSelector(UserControl):
    """Date selector."""

    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self.initialDate = datetime.date.today()
        self.date = str(self.initialDate.day)
        self.month = str(self.initialDate.month)
        self.year = str(self.initialDate.year)

        self.day_dropdown = get_dropdown(
            lbl=DAY_LBL,
            hint="",
            on_change=self.on_date_set,
            items=[str(day) for day in range(1, 32)],
            width=50,
            initial_value=self.date,
        )

        self.month_dropdown = get_dropdown(
            lbl=MONTH_LBL,
            on_change=self.on_month_set,
            items=[str(month) for month in range(1, 13)],
            width=50,
            initial_value=self.month,
        )

        self.year_dropdown = get_dropdown(
            lbl=YEAR_LBL,
            on_change=self.on_year_set,
            items=[str(year) for year in range(2022, 2027)],
            width=100,
            initial_value=self.year,
        )

    def on_date_set(self, e):
        self.date = e.control.value

    def on_month_set(self, e):
        self.month = e.control.value

    def on_year_set(self, e):
        self.year = e.control.value

    def build(self):
        self.view = Container(
            content=Column(
                controls=[
                    Text(self.label, size=fonts.BODY_2_SIZE),
                    Row(
                        [
                            self.day_dropdown,
                            self.month_dropdown,
                            self.year_dropdown,
                        ],
                    ),
                ]
            ),
        )
        return self.view

    def set_date(self, date: Optional[datetime.date] = None):
        if date is None:
            return
        self.date = str(date.day)
        self.month = str(date.month)
        self.year = str(date.year)
        self.day_dropdown.value = self.date
        self.month_dropdown.value = self.month
        self.year_dropdown.value = self.year

        self.update()

    def get_date(self) -> Optional[datetime.date]:
        """Return the selected timeframe."""
        if self.year is None or self.month is None or self.date is None:
            return None

        date = datetime.date(
            year=int(self.year),
            month=int(self.month),
            day=int(self.date),
        )
        return date
