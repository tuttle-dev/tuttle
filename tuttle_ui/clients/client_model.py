from dataclasses import dataclass
from typing import Optional


@dataclass
class Client:
    """A client the freelancer has contracted with."""

    id: Optional[int]
    title: str
    invoicing_contact_id: Optional[int]


def create_client_from_title(title: str) -> Client:
    return Client(id=1, title=title, invoicing_contact_id=None)
