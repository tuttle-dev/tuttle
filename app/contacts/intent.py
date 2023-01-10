from typing import Optional, Mapping

from core.abstractions import ClientStorage
from core.models import IntentResult
from .model import Contact
from .data_source import ContactDataSource

from tuttle.model import (
    Address,
)


class ContactsIntent:
    def __init__(self, local_storage: ClientStorage):
        self.data_source = ContactDataSource()
        self.local_storage = local_storage

    def get_all_contacts_as_map(self) -> Mapping[int, Contact]:
        result = self.data_source.get_all_contacts_as_map()
        if result.was_intent_successful:
            return result.data
        else:
            return {}

    def get_contact_by_id(self, contactId) -> IntentResult:
        result = self.data_source.get_contact_by_id(contactId)
        if not result.was_intent_successful:
            result.error_msg = "--TODO-- error message"
        return result

    def save_contact(self, contact: Contact) -> IntentResult:
        if not contact.first_name or not contact.last_name:
            return IntentResult(
                was_intent_successful=False,
                error_msg_if_err="Failed to save contact. A name is required.",
                data=None,
            )
        if contact.address.is_empty:
            return IntentResult(
                was_intent_successful=False,
                error_msg_if_err="Failed to save contact. Please specify the address.",
                data=None,
            )
        return self.data_source.save_contact(contact=contact)
