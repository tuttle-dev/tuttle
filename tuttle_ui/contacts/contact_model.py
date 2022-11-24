import textwrap
from dataclasses import dataclass
from typing import Optional
from core.models import Address


@dataclass
class Contact:
    """An entry in the address book."""

    id: Optional[int]
    first_name: Optional[str]
    last_name: Optional[str]
    company: Optional[str]
    email: Optional[str]
    address_id: Optional[int]

    @property
    def name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        elif self.company:
            return self.company
        else:
            return None
