import enum
import datetime
import textwrap
from flet import View
from typing import Callable
from dataclasses import dataclass
from typing import Optional


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


# TODO: should this class be here?
class IntentResult:
    """Wraps the result of a view's intent

    data - the result else None
    was_intent_successful - True if the operation did not encounter any error
    error_msg_if_err - error message to be shown to the user, typically set by the intent instance
    log_message - optional message to be logged, typically set by data_source instance, is not shown to the user
    """

    def __init__(
        self,
        data: Optional[any] = None,
        was_intent_successful: bool = False,
        error_msg: str = "",
        log_message: str = "",
    ):
        super().__init__()
        self.error_msg = error_msg
        self.data = data
        self.was_intent_successful = was_intent_successful
        self.log_message = log_message


@dataclass
class RouteView:
    """A utility class that defines a route view"""

    view: View
    keep_back_stack: bool
    on_window_resized: Callable
