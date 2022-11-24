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
