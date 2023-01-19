"""helper functions for manipulating dates"""
import warnings

warnings.warn(
    "This module is deprecated and will be removed in the future",
    DeprecationWarning,
    stacklevel=2,
)

import datetime

from tuttle.dev import deprecated

DAYS_IN_A_WEEK = 7


@deprecated(
    "reinventing the square wheel antipattern: use existing functions in Python standard library"
)
def get_date_as_str(date: datetime.date, hide_year: bool = False):
    # FIXME: no need to reinvent the wheel here
    if hide_year:
        return f"{date.day} / {date.month}"
    else:
        return f"{date.day} / {date.month} / {date.year}"


@deprecated(
    "reinventing the square wheel antipattern: use existing functions in Python standard library"
)
def get_last_seven_days():
    today = datetime.date.today()
    last_seven = []
    i = DAYS_IN_A_WEEK - 1
    while i >= 0:
        past_day = today - datetime.timedelta(days=i)
        last_seven.append(get_date_as_str(past_day, hide_year=True))
        i = i - 1
    return last_seven
