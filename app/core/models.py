import warnings

from tuttle.model import Cycle, TimeUnit

warnings.warn(
    "wastebasket module, content will be moved to other modules",
    DeprecationWarning,
    stacklevel=2,
)

from typing import Callable, Optional

import datetime
import enum
from dataclasses import dataclass

from flet import View

from tuttle.dev import deprecated


@deprecated("syntactic salt: use list(Enum) instead")
def get_cycle_values_as_list():
    values = []
    for c in Cycle:
        values.append(str(c))
    return values


@deprecated("square wheel reinvention antipattern: use Enum[value] instead")
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


@deprecated("syntactic salt: use list(Enum) instead")
def get_time_unit_values_as_list():
    values = []
    for t in TimeUnit:
        values.append(str(t))
    return values


@deprecated("square wheel reinvention antipattern: use Enum[value] instead")
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
