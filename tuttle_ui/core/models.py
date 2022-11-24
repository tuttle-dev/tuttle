import enum
import datetime
import textwrap
from dataclasses import dataclass
from typing import Optional
from res.strings import (
    HOURLY,
    HOUR,
    DAILY,
    DAY,
    WEEKLY,
    MINUTE,
    MONTHLY,
    QUARTERLY,
    YEARLY,
)


class Cycle(enum.Enum):
    hourly = HOURLY
    daily = DAILY
    weekly = WEEKLY
    monthly = MONTHLY
    quarterly = QUARTERLY
    yearly = YEARLY

    def __str__(self):
        return str(self.value)


def get_cycle_values_as_list():
    values = []
    for c in Cycle:
        values.append(str(c))
    return values


def get_cycle_from_value(value: str) -> Optional[Cycle]:
    if value == Cycle.daily.value:
        return Cycle.daily
    elif value == Cycle.hourly.value:
        return Cycle.hourly
    elif value == Cycle.weekly.value:
        return Cycle.weekly
    elif value == Cycle.monthly.value:
        return Cycle.monthly
    elif value == Cycle.yearly.value:
        return Cycle.yearly
    else:
        return None


class TimeUnit(enum.Enum):
    minute = MINUTE
    hour = HOUR
    day = DAY

    def to_timedelta(self):
        if self == TimeUnit.minute:
            return datetime.timedelta(minutes=1)
        elif self == TimeUnit.hour:
            return datetime.timedelta(hours=1)
        elif self == TimeUnit.day:
            return datetime.timedelta(days=1)

    def __str__(self):
        return str(self.value)


def get_time_unit_values_as_list():
    values = []
    for t in TimeUnit:
        values.append(str(t))
    return values


def get_time_unit_from_value(value: str) -> Optional[TimeUnit]:
    if value == TimeUnit.day.value:
        return TimeUnit.day
    elif value == TimeUnit.hour.value:
        return TimeUnit.hour
    elif value == TimeUnit.minute.value:
        return TimeUnit.minute
    else:
        return None


@dataclass
class Address:
    """Postal address."""

    id: Optional[int]
    street: str
    number: str
    city: str
    postal_code: str
    country: str

    @property
    def printed(self):
        """Print address in common format."""
        return textwrap.dedent(
            f"""
        {self.street} {self.number}
        {self.postal_code} {self.city}
        {self.country}
        """
        )

    @property
    def html(self):
        """Print address in common format."""
        return textwrap.dedent(
            f"""
        {self.street} {self.number}<br>
        {self.postal_code} {self.city}<br>
        {self.country}
        """
        )
