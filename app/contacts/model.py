import textwrap
from dataclasses import dataclass
from typing import Optional

from core.models import Address, get_empty_address


@dataclass
class Contact:
    """An entry in the address book."""

    id: Optional[int]
    first_name: str
    last_name: str
    company: Optional[str]
    email: Optional[str]
    address_id: Optional[int]
    address: Optional[Address]

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

    def print_address(self, onlyAddress: bool = False):
        """Print address in common format."""
        if self.address is None:
            return ""

        if onlyAddress:
            return textwrap.dedent(
                f"""
                {self.address.street} {self.address.number}
                {self.address.postal_code} {self.address.city}
                {self.address.country}"""
            )

        return textwrap.dedent(
            f"""
        {self.name}
        {self.company}
        {self.address.street} {self.address.number}
        {self.address.postal_code} {self.address.city}
        {self.address.country}
        """
        )


def get_empty_contact():
    """helper function, returns an empty contact for an editor"""
    address = get_empty_address()
    contact = Contact(
        id=None,
        first_name="",
        last_name="",
        company="",
        email="",
        address=address,
        address_id=address.id,
    )
    return contact
