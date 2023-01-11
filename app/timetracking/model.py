"""Helper models for timetracking"""

from dataclasses import dataclass
from preferences.model import CloudAccounts


@dataclass
class CloudCalendarInfo:
    account: str
    calendar_name: str
    provider: CloudAccounts
    password: str
