from core.models import Address
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    title: str
    name: str
    email: str
    phone: str
    address: Optional[Address]
