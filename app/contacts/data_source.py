from typing import Optional
from pathlib import Path
import faker
from loguru import logger

from core.models import IntentResult
from core.abstractions import SQLModelDataSourceMixin
from .model import Contact

from tuttle.model import Address
from tuttle.dev import deprecated


class ContactDataSource(SQLModelDataSourceMixin):
    def __init__(
        self,
    ):
        super().__init__()

    def get_all_contacts_as_map(self) -> IntentResult:
        contacts = self.query(Contact)
        result = {contact.id: contact for contact in contacts}
        return IntentResult(
            was_intent_successful=True,
            data=result,
        )

    @deprecated
    def get_contact_by_id(self, contactId) -> IntentResult:
        raise NotImplementedError("This method is deprecated.")

    def save_contact(self, contact: Contact) -> IntentResult:
        self.store(contact)
        logger.info(f"Saved contact: {contact}")
        return IntentResult(
            was_intent_successful=True,
            data=contact,
        )
