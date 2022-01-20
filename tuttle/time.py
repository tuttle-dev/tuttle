import enum


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
