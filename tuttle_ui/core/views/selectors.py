from flet import (
    UserControl,
    Container,
    Row,
    Dropdown,
    dropdown,
    TextStyle,
    padding,
    Text,
    Column,
)
from typing import List, Callable, Optional
from res import fonts, spacing, colors
from res.strings import DAY_LBL, MONTH_LBL, YEAR_LBL
import datetime


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
    onChange: Callable,
    items: List[str],
    hint: Optional[str] = "",
    width: Optional[int] = None,
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
        width=width,
        content_padding=padding.all(spacing.SPACE_XS),
        error_style=TextStyle(size=fonts.BODY_2_SIZE, color=colors.ERROR_COLOR),
    )


class DateSelector(UserControl):
    """Date selector."""

    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self.date = ""
        self.month = ""
        self.year = ""

        self.day_dropdown = get_dropdown(
            lbl=DAY_LBL,
            hint="",
            onChange=self.on_date_set,
            items=[str(day) for day in range(1, 32)],
            width=50,
        )

        self.month_dropdown = get_dropdown(
            lbl=MONTH_LBL,
            onChange=self.on_month_set,
            items=[str(month) for month in range(1, 13)],
            width=50,
        )

        self.year_dropdown = get_dropdown(
            lbl=YEAR_LBL,
            onChange=self.on_year_set,
            items=[str(year) for year in range(2022, 2027)],
            width=100,
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
