import faker

from typing import Optional

from core.models import Address, IntentResult
from .model import Contact


class ContactDataSourceImpl:
    def __init__(self):
        self.contacts = {}

    def get_all_contacts_as_map(self) -> IntentResult:
        self._set_dummy_contacts()
        return IntentResult(was_intent_successful=True, data=self.contacts)

    def get_contact_by_id(self, contactId) -> IntentResult:
        fake = faker.Faker(["de_DE", "en_US", "es_ES", "fr_FR", "it_IT", "sv_SE"])
        c = self._get_fake_contact(fake, contactId)
        return IntentResult(was_intent_successful=True, data=c)

    def save_contact(self, contact: Contact) -> IntentResult:
        if contact.id is None:
            # then create a new contact and set ids
            contact.id = 1
            contact.address_id = 1
            contact.address.id = 1
        return IntentResult(was_intent_successful=True, data=contact)

    """DUMMY CONTENT BELOW ---  DELETE ALL"""

    def _set_dummy_contacts(self):
        fake = faker.Faker(["de_DE", "en_US", "es_ES", "fr_FR", "it_IT", "sv_SE"])
        self.contacts.clear()
        total = 12
        for i in range(total):
            c = self._get_fake_contact(fake, i)
            self.contacts[c.id] = c

    def _get_fake_contact(self, fake, id: int):
        street_line, city_line = fake.address().splitlines()
        a = Address(
            id=id,
            street=street_line.split(" ")[0],
            number=street_line.split(" ")[1],
            city=city_line.split(" ")[1],
            postal_code=city_line.split(" ")[0],
            country=fake.country(),
        )
        first_name, last_name = fake.name().split(" ", 1)
        c = Contact(
            id=id,
            first_name=first_name,
            last_name=last_name,
            email=fake.email(),
            company=fake.company(),
            address_id=a.id,
            address=a,
        )
        return c
