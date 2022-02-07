"""View classes."""

from typing import List, Optional

from dataclasses import dataclass
import datetime


@dataclass
class Event:

    title: str
    date: datetime.date
    description: str


@dataclass
class Timeline:
    events: List[Event]
