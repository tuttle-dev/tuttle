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

    def get_start_date_as_str(self) -> str:
        return self.start_date.strftime("%m/%d/%Y")

    def get_end_date_as_str(self) -> str:
        return self.end_date.strftime("%m/%d/%Y")
