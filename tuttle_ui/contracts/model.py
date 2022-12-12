from dataclasses import dataclass
import datetime
from typing import Optional
from pydantic import condecimal
from decimal import Decimal
from core.models import Cycle, TimeUnit
from res.strings import ACTIVE, COMPLETED, UPCOMING, ALL
from clients.model import Client


@dataclass
class Contract:
    """A contract defines the business conditions of a project"""

    id: Optional[int]
    title: str
    signature_date: datetime.date
    start_date: datetime.date
    end_date: Optional[datetime.date]
    client_id: int
    client: Client
    rate: condecimal(decimal_places=2)
    currency: str
    VAT_rate: Decimal
    unit: TimeUnit
    units_per_workday: int
    volume: Optional[int]
    term_of_payment: Optional[int]
    billing_cycle: Cycle = Cycle.hourly
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
            return ACTIVE
        elif self.is_upcoming():
            return UPCOMING
        elif self.is_completed:
            return COMPLETED
        else:
            # default
            return ALL
