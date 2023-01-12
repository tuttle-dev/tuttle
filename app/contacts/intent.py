from typing import Mapping
from tuttle.dev import deprecated
from core.models import IntentResult
from .data_source import ContactDataSource

from tuttle.model import (
    Contact,
)


class ContactsIntent:
    def __init__(
        self,
    ):
        self.data_source = ContactDataSource()

    def get_all_contacts_as_map(self) -> Mapping[int, Contact]:
        result = self.data_source.get_all_contacts()
        if result.was_intent_successful:
            contacts = result.data
            contacts_as_map = {contact.id: contact for contact in contacts}
            return contacts_as_map
        else:
            return {}

    @deprecated
    def get_contact_by_id(self, contactId) -> IntentResult:
        return IntentResult(was_intent_successful=False, error_msg="Deprecated method!")

    def save_contact(self, contact: Contact) -> IntentResult:
        if not contact.first_name or not contact.last_name:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to save contact. A name is required.",
                data=None,
            )
        if contact.address.is_empty:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to save contact. Please specify the address.",
                data=None,
            )
        return self.data_source.save_contact(contact=contact)
