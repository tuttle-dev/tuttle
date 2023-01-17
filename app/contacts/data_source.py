from core.intent_result import IntentResult
from core.abstractions import SQLModelDataSourceMixin
from tuttle.model import Contact
from typing import List, Union


class ContactDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the Contact model in the database"""

    def __init__(self):
        super().__init__()

    def get_all_contacts(self) -> IntentResult[List[Contact]]:
        """Fetches all existing contacts from the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  List[Contact] if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            contacts = self.query(Contact)
            return IntentResult(
                was_intent_successful=True,
                data=contacts,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContactDataSource.get_all_contacts {e.__class__.__name__}",
                exception=e,
            )

    def save_contact(self, contact: Contact) -> IntentResult[Union[Contact, None]]:
        """Store a contact in the data source.

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  Contact if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            self.store(contact)
            return IntentResult(
                was_intent_successful=True,
                data=contact,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContactDataSource.save_contact {e.__class__.__name__}",
                exception=e,
            )

    def delete_contact_by_id(self, contact_id) -> IntentResult[None]:
        """Deletes a contact with the given id from the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            self.delete_by_id(Contact, contact_id)
            return IntentResult(was_intent_successful=True)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContactDataSource.delete_contact_by_id {e.__class__.__name__}",
                exception=e,
            )
