from dataclasses import dataclass
import datetime

from typing import Optional
from contracts.model import Contract
from clients.model import Client


@dataclass
class Project:
    id: Optional[int]
    contract_id: int
    contract: Contract
    title: str
    description: str
    unique_tag: str
    start_date: datetime.date
    end_date: datetime.date
    is_completed: bool = False

    def get_start_date_as_str(self) -> str:
        return self.start_date.strftime("%m/%d/%Y")

    def get_end_date_as_str(self) -> str:
        return self.end_date.strftime("%m/%d/%Y")

    def is_active(self) -> bool:
        today = datetime.date.today()
        return self.end_date > today

    def is_upcoming(self) -> bool:
        today = datetime.date.today()
        return self.start_date > today

    def get_status(self) -> str:
        if self.is_active():
            return "Active"
        elif self.is_upcoming():
            return "Upcoming"
        elif self.is_completed:
            return "Completed"
        else:
            # default
            return "All"

    def get_brief_description(self):
        if len(self.description) <= 108:
            return self.description
        else:
            return f"{self.description[0:108]}..."
