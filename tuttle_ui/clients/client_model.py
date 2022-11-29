from dataclasses import dataclass
from typing import Optional
from contacts.contact_model import Contact, get_empty_contact


@dataclass
class Client:
    """A client the freelancer has contracted with."""

    id: Optional[int]
    title: str
    invoicing_contact_id: Optional[int]
    invoicing_contact: Optional[Contact] = None


def get_empty_client():
    """helper function for creating an empty client object used in editor"""
    return Client(
        id=None,
        title="",
        invoicing_contact_id=None,
        invoicing_contact=get_empty_contact(),
    )
