from typing import Optional
from pathlib import Path
import faker

from core.models import Address, IntentResult
from core.abstractions import SQLModelDataSourceMixin
from .model import Contact


class ContactDataSource(SQLModelDataSourceMixin):
    def __init__(
        self,
        db_path: str = f"sqlite:///{Path('app/tmp/db.sqlite').resolve()}",
    ):
        super().__init__(db_path=db_path)

    def get_all_contacts_as_map(self) -> IntentResult:
        contacts = self.query(Contact)
        return IntentResult(
            was_intent_successful=True,
            data={contact.id: contact for contact in contacts},
        )

    def get_contact_by_id(self, contactId) -> IntentResult:
        fake = faker.Faker(["de_DE", "en_US", "es_ES", "fr_FR", "it_IT", "sv_SE"])
        c = self._get_fake_contact(fake, contactId)
        return IntentResult(
            was_intent_successful=True,
            data=c,
        )

    def save_contact(self, contact: Contact) -> IntentResult:
        if contact.id is None:
            # then create a new contact and set ids
            contact.id = 1
            contact.address_id = 1
            contact.address.id = 1
        return IntentResult(
            was_intent_successful=True,
            data=contact,
        )
