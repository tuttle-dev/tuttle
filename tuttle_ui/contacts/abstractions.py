from abc import ABC, abstractmethod

from typing import Optional, Mapping

from core.abstractions import ClientStorage
from core.models import Address, IntentResult
from .contact_model import Contact


class ContactDataSource(ABC):
    """Defines methods for instantiating, viewing, updating, saving and deleting contacts"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_all_contacts_as_map(
        self,
    ) -> IntentResult:
        """if successful, returns contacts as data mapped as contactId -> contact"""
        pass

    @abstractmethod
    def save_contact(
        self,
        contact: Contact = None,
    ) -> IntentResult:
        """attempts to create or update a contact

        if contact passed has an id, then it is an update operation
        returns the new /updated contact as data if successful
        """
        pass

    @abstractmethod
    def get_contact_by_id(self, contactId) -> IntentResult:
        """if successful, returns the contact as data"""
        pass


class ContactsIntent(ABC):
    """Handles contact view intents"""

    def __init__(self, data_source: ContactDataSource, local_storage: ClientStorage):
        super().__init__()
        self.local_storage = local_storage
        self.data_source = data_source

    @abstractmethod
    def get_all_contacts_as_map(
        self,
    ) -> Mapping[int, Contact]:
        """if successful, returns contacts as data mapped as contactId -> contact"""
        pass

    @abstractmethod
    def save_contact(
        self,
        contact: Contact = None,
    ) -> IntentResult:
        """attempts to create or update a contact

        if contact passed has an id, then it is an update operation
        returns the new /updated contact as data if successful
        """
        pass

    @abstractmethod
    def get_contact_by_id(self, contactId) -> IntentResult:
        """if successful, returns the contact as data"""
        pass
