from typing import Mapping
from core.intent_result import IntentResult
from .data_source import ContactDataSource

from tuttle.model import (
    Contact,
)


class ContactsIntent:
    """Handles Contact C_R_U_D intents

    Intents handled (Methods)
    ---------------

    get_all_contacts_as_map_intent
        fetching existing contacts as a map of contact IDs to contact

    save_contact_intent
        saving the contact

    delete_contact_by_id_intent
        deleting a contact given it's id
    """

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

    def get_all_contacts_as_map_intent(self) -> Mapping[int, Contact]:
        result = self._data_source.get_all_contacts()
        if result.was_intent_successful:
            contacts = result.data
            contacts_as_map = {contact.id: contact for contact in contacts}
            return contacts_as_map
        else:
            result.log_message_if_any()
            return {}

    def save_contact_intent(self, contact: Contact) -> IntentResult:
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

    def delete_contact_by_id_intent(self, contact_id):
        result: IntentResult = self._data_source.delete_contact_by_id(contact_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete the contact! please retry"
            result.log_message_if_any()
        return result
