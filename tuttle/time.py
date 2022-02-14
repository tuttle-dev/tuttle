import enum
import datetime


class Cycle(enum.Enum):
    hourly = 0
    daily = 1
    weekly = 2
    monthly = 3
    quarterly = 4
    yearly = 5


class TimeUnit(enum.Enum):
    minute = 0
    hour = 1
    day = 2

    def to_timedelta(self):
        if self == TimeUnit.minute:
            return datetime.timedelta(minutes=1)
        elif self == TimeUnit.hour:
            return datetime.timedelta(hours=1)
        elif self == TimeUnit.day:
            return datetime.timedelta(days=1)
