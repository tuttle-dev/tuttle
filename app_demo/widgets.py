import datetime
import pytz

from flet import (
    UserControl,
    Container,
    Row,
    Icon,
    IconButton,
    Text,
    Dropdown,
)
from flet import icons, colors, dropdown


class DateSelector(UserControl):
    """Timeframe selector."""

    def __init__(
        self,
        preset: datetime.date = None,
    ):
        super().__init__()

        self.preset = preset
        self.day_dropdown = Dropdown(
            label="D",
            options=[dropdown.Option(day) for day in range(1, 32)],
            width=50,
        )
        if self.preset:
            self.day_dropdown.value = str(self.preset.day)

        self.month_dropdown = Dropdown(
            label="M",
            options=[dropdown.Option(month) for month in range(1, 13)],
            width=50,
        )
        if self.preset:
            self.month_dropdown.value = str(self.preset.month)

        self.year_dropdown = Dropdown(
            label="Y",
            options=[dropdown.Option(year) for year in range(2015, 2025)],
            width=100,
        )
        if self.preset:
            self.year_dropdown.value = str(self.preset.year)

        self.view = Container(
            content=Row(
                [
                    Icon(
                        icons.CALENDAR_MONTH,
                    ),
                    self.day_dropdown,
                    self.month_dropdown,
                    self.year_dropdown,
                ],
                alignment="center",
            ),
            padding=10,
        )

    def build(self):
        return self.view

    def get_date(
        self,
        as_datetime: bool = False,
    ):
        """Return the selected timeframe."""
        date = datetime.date(
            year=int(self.year_dropdown.value),
            month=int(self.month_dropdown.value),
            day=int(self.day_dropdown.value),
        )
        if as_datetime:
            date = datetime.datetime.combine(date, datetime.time())
            date = pytz.utc.localize(date)

        return date
