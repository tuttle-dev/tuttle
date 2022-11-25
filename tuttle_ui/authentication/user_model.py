from core.models import Address
from dataclasses import dataclass


@dataclass
class User:
    id: int
    title: str
    name: str
    email: str
    phone: str
    address: Address
