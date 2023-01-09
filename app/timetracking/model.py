"""Helper models for timetracking"""

from dataclasses import dataclass


@dataclass
class ICloudCalendarInfo:
    account: str
    calendar_name: str
    password: str
