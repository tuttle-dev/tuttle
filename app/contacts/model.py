import textwrap
from dataclasses import dataclass
from typing import Optional

from tuttle.model import (
    Address,
    Contact,
)

from core.models import get_empty_address

# TODO: make this a class method of Contact
def get_empty_contact():
    """helper function, returns an empty contact for an editor"""
    # TODO: make this a class method of Address
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
