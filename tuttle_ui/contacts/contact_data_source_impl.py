import faker

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
        address_id: Optional[int],
        street: str,
        number: str,
        city: str,
        postal_code: str,
        country: str,
    ) -> ContactIntentsResult:
        id = 1
        if address_id is not None:
            # this is an update
            id = address_id
        address = Address(
            id=id,
            street=street,
            number=number,
            city=city,
            postal_code=postal_code,
            country=country,
        )
        return ContactIntentsResult(wasIntentSuccessful=True, data=address)

    def save_contact(
        self,
        contact_id: Optional[int],
        first_name: str,
        last_name: str,
        company: Optional[str],
        email: str,
        address: Optional[Address] = None,
    ) -> ContactIntentsResult:
        id = 1
        if contact_id is not None:
            # this is an update
            id = contact_id
        contact = Contact(
            id=id,
            first_name=first_name,
            last_name=last_name,
            company=company,
            email=email,
            address_id=None if address is None else address.id,
            address=address,
        )
        return ContactIntentsResult(wasIntentSuccessful=True, data=contact)

    def create_contact_and_address(self, contact: Contact) -> ContactIntentsResult:
        contact.id = 2
        contact.address_id = 2
        contact.address.id = contact.address_id
        return ContactIntentsResult(wasIntentSuccessful=True, data=contact)

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
        fake = faker.Faker(["de_DE", "en_US", "es_ES", "fr_FR", "it_IT", "sv_SE"])
        self.contacts.clear()
        total = 16
        for i in range(total):
            street_line, city_line = fake.address().splitlines()
            a = Address(
                id=i,
                street=street_line.split(" ")[0],
                number=street_line.split(" ")[1],
                city=city_line.split(" ")[1],
                postal_code=city_line.split(" ")[0],
                country=fake.country(),
            )
            first_name, last_name = fake.name().split(" ", 1)
            c = Contact(
                id=i,
                first_name=first_name,
                last_name=last_name,
                email=fake.email(),
                company=fake.company(),
                address_id=a.id,
                address=a,
            )
            self.contacts[c.id] = c
