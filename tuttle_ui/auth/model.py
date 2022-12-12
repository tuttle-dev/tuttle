from typing import Optional
from core.models import Address
from dataclasses import dataclass


@dataclass
class User:
    id: Optional[int]
    name: str
    subtitle: str
    email: str
    phone_number: str
    address_id: Optional[int]
    address: Optional[Address]
    website: Optional[str] = ""
    VAT_number: Optional[str] = ""
