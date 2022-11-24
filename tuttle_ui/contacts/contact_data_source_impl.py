from .abstractions import ContactDataSource
from .contact_model import Contact
from .utils import ContactIntentsResult
from typing import Mapping, Optional
from core.models import Address

# TODO
class ContactDataSourceImpl(ContactDataSource):
    def __init__(self):
        super().__init__()
        self.contacts: Mapping[str, Contact] = {}

    def get_all_contacts_as_map(
        self,
    ) -> ContactIntentsResult:
        self._set_dummy_contacts()
        return ContactIntentsResult(wasIntentSuccessful=True, data=self.contacts)

    def save_address(
        self,
        address_id: Optional[str],
        street: str,
        number: str,
        city: str,
        postal_code: str,
        country: str,
    ) -> ContactIntentsResult:
        id = 1
        if address_id:
            # this is an update
            id = int(address_id)
        address = Address(
            id=id,
            street=street,
            number=number,
            city=city,
            postal_code=postal_code,
            country=country,
        )
        return ContactIntentsResult(wasIntentSuccessful=True, data=address.id)

    def save_contact(
        self,
        contact_id: Optional[str],
        first_name: str,
        last_name: str,
        company: Optional[str],
        email: str,
        address_id: Optional[int],
    ) -> ContactIntentsResult:
        id = 1
        if contact_id:
            # this is an update
            id = int(contact_id)
        contact = Contact(
            id=id,
            first_name=first_name,
            last_name=last_name,
            company=company,
            email=email,
            address_id=address_id,
        )
        return ContactIntentsResult(wasIntentSuccessful=True, data=contact.id)

    def set_contact_address_id(
        self, address_id: str, contact_id: str
    ) -> ContactIntentsResult:
        return ContactIntentsResult(wasIntentSuccessful=True)

    def get_contact_by_id(self, contactId) -> ContactIntentsResult:
        i = int(contactId)
        contact = Contact(
            id=i,
            first_name="Sample ",
            last_name="Contact",
            email="sample@contact.com",
            address=None,
            address_id=None,
        )
        return ContactIntentsResult(wasIntentSuccessful=True, data=contact)

    def get_address_by_id(self, addressId) -> ContactIntentsResult:
        id = int(addressId)
        address = Address(
            id=id,
            street="Sample street",
            number="1234",
            city="Berlin",
            postal_code="45600",
            country="Germany",
        )
        return ContactIntentsResult(wasIntentSuccessful=True, data=address)

    """DUMMY CONTENT BELOW ---  DELETE ALL"""

    def _set_dummy_contacts(self):
        self.contacts.clear()
        total = 50
        for i in range(total):
            a = Address(
                id=i,
                street=f"street 12{i}",
                number=f"445{i}",
                city="Berlin",
                postal_code=f"365{i}",
                country="Germany",
            )
            c = Contact(
                id=i,
                first_name=f"Saidah",
                last_name=f"Van Lierop",
                email="sample@contact.com",
                company=f"wellpalcreative",
                address_id=a.id,
                address=a,
            )
            self.contacts[c.id] = c
