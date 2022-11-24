from dataclasses import dataclass
import datetime
from typing import Optional
from pydantic import condecimal
from decimal import Decimal
from core.model_utils.time import TimeUnit, Cycle
from res.strings import ACTIVE, COMPLETED, UPCOMING, ALL


@dataclass
class Contract:
    """A contract defines the business conditions of a project"""

    id: int
    title: str
    signature_date: Optional[datetime.date]
    start_date: Optional[datetime.date]
    end_date: Optional[datetime.date]
    client_id: Optional[int]
    rate: Optional[condecimal(decimal_places=2)]
    currency: Optional[str]
    VAT_rate: Optional[Decimal]
    unit: Optional[TimeUnit]
    units_per_workday: Optional[int]
    volume: Optional[int]
    term_of_payment: Optional[int]
    billing_cycle: Optional[Cycle]
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


# NOTE - other fields are marked as optional to support quick creation of a contract using just title
def create_contract_from_title(title: str) -> Contract:
    return Contract(
        id=1,
        title=title,
        signature_date=None,
        start_date=None,
        end_date=None,
        client_id=None,
        rate=None,
        currency=None,
        VAT_rate=None,
        unit=None,
        units_per_workday=None,
        volume=None,
        term_of_payment=None,
        billing_cycle=None,
    )
