from typing import Optional
from pathlib import Path
from loguru import logger

from core.models import IntentResult
from core.abstractions import SQLModelDataSourceMixin


from tuttle.model import Contact


class ContactDataSource(SQLModelDataSourceMixin):
    """This class provides the data source for the Contact model"""

    def __init__(self):
        """Initialize the ContactDataSource object"""
        super().__init__()

    def get_all_contacts(self) -> IntentResult:
        """Returns data as a list of all existing contacts"""
        try:
            contacts = self.query(Contact)
            return IntentResult(
                was_intent_successful=True,
                data=contacts,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContactDataSource.get_all_contacts {e}",
            )

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

    def delete_contact_by_id(self, contact_id):
        """Attempts to delete the contact associated with the given id"""
        try:
            self.delete_by_id(Contact, contact_id)
            return IntentResult(was_intent_successful=True)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContactDataSource.delete_contact_by_id {e}",
            )
