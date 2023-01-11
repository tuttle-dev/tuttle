from typing import Optional
from pathlib import Path
from loguru import logger

from core.models import IntentResult
from core.abstractions import SQLModelDataSourceMixin

from tuttle.dev import deprecated
from tuttle.model import Contact


class ContactDataSource(SQLModelDataSourceMixin):
    """This class provides the data source for the Contact model"""

    def __init__(self):
        """Initialize the ContactDataSource object"""
        super().__init__()

    def get_all_contacts_as_map(self) -> IntentResult:
        """Retrieve all contacts and return them as a map with the contact's id as the key.

        Returns:
            IntentResult : A IntentResult object representing the outcome of the operation
        """
        contacts = self.query(Contact)
        result = {contact.id: contact for contact in contacts}
        return IntentResult(
            was_intent_successful=True,
            data=result,
        )

    @deprecated
    def get_contact_by_id(self, contactId) -> IntentResult:
        """Retrieve a contact by their id.

        This method is deprecated.

        Returns:
            IntentResult : A IntentResult object representing the outcome of the operation
        """
        raise NotImplementedError("This method is deprecated.")

    def save_contact(self, contact: Contact) -> IntentResult:
        """Store a contact in the data source.

        Args:
            contact (Contact): The contact to be stored.

        Returns:
            IntentResult : A IntentResult object representing the outcome of the operation
        """
        self.store(contact)
        logger.info(f"Saved contact: {contact}")
        return IntentResult(
            was_intent_successful=True,
            data=contact,
        )
