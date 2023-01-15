import enum
import datetime
from flet import View
from typing import Callable
from dataclasses import dataclass
from typing import Optional

from tuttle.dev import deprecated


class Cycle(enum.Enum):
    hourly = "Hourly"
    daily = "Daily"
    weekly = "Weekly"
    monthly = "Monthly"
    quarterly = "Quarterly"
    yearly = "Yearly"

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
    minute = "Minute"
    hour = "Hour"
    day = "Day"

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
class RouteView:
    """A utility class that defines a route view"""

    view: View
    keep_back_stack: bool
    on_window_resized: Callable


@deprecated
class TuttleDateRange:
    """ "Wraps a start and from date"""

    # TODO: remove this class, a tuple will do

    def __init__(self, from_date: datetime.date, to_date: datetime.date) -> None:
        self.from_date: datetime.date = from_date
        self.to_date: datetime.date = to_date

    def is_valid(self):
        return self.from_date < self.to_date
