from dataclasses import dataclass
import datetime


@dataclass
class Project:
    id: int
    contract_id: int
    client_id: int
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
