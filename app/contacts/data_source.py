from typing import Optional
from pathlib import Path
from loguru import logger

from core.models import IntentResult
from core.abstractions import SQLModelDataSourceMixin

from tuttle.dev import deprecated
from tuttle.model import Contact


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
