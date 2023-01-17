from typing import Mapping, Union
from core.intent_result import IntentResult
from .data_source import ContactDataSource

from tuttle.model import (
    Contact,
)


class ContactsIntent:
    """Handles Contact C_R_U_D intents"""

    def __init__(
        self,
    ):
        """
        Attributes
        ----------
        _data_source : ContactDataSource
            reference to the contact's data source
        """
        self._data_source = ContactDataSource()

    def get_all_contacts_as_map(self) -> Mapping[int, Contact]:
        """
        Returns:
            Mapping[int, Contact]:
                A map of contact IDs to contact
        """
        result = self._data_source.get_all_contacts()
        if result.was_intent_successful:
            contacts = result.data
            contacts_as_map = {contact.id: contact for contact in contacts}
            return contacts_as_map
        else:
            result.log_message_if_any()
            return {}

    def save_contact(self, contact: Contact) -> IntentResult[Union[Contact, None]]:
        """
        Args:
            contact (Contact): Contact to be saved

        Returns:
            IntentResult[Union[Contact, None]]:
                was_intent_successful : bool
                data :  Contact if was_intent_successful else None
                error_msg : str  if an error or exception occurs
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        if not contact.first_name or not contact.last_name:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Saving contact failed. A name is required.",
            )
        if contact.address.is_empty:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Saving contact failed. Please specify the address.",
            )
        result = self._data_source.save_contact(contact=contact)
        if not result.was_intent_successful:
            result.error_msg = "Saving contact failed. Please retry"
            result.log_message_if_any()
        return result

    def delete_contact_by_id(self, contact_id) -> IntentResult[None]:
        """
        Args:
            contact_id : ID of the contact to be deleted

        Returns:
            IntentResult[None]:
                was_intent_successful : bool
                error_msg : str  if an error or exception occurs
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        result: IntentResult = self._data_source.delete_contact_by_id(contact_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete the contact! please retry"
            result.log_message_if_any()
        return result
