from abc import ABC, abstractmethod
from typing import Optional, Mapping

from core.abstractions import ClientStorage
from core.models import IntentResult
from .client_model import Client
from contacts.contact_model import Contact


class ClientDataSource(ABC):
    """Defines methods for instantiating, viewing, updating, saving and deleting clients"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_all_clients_as_map(
        self,
    ) -> IntentResult:
        """if successful, returns clients as data mapped as clientId -> client"""
        pass

    @abstractmethod
    def save_client(
        self,
        client: Client,
    ) -> IntentResult:
        """attempts to create or update a client

        if client passed has id, then it is an update operation
        returns the new /updated client as data if successful
        """
        pass

    @abstractmethod
    def get_client_by_id(self, clientId) -> IntentResult:
        """if successful, returns the client as data"""
        pass


class ClientsIntent(ABC):
    """Handles client view intents"""

    def __init__(self, data_source: ClientDataSource, local_storage: ClientStorage):
        super().__init__()
        self.local_storage = local_storage
        self.data_source = data_source

    @abstractmethod
    def get_all_clients_as_map(
        self,
    ) -> Mapping[int, Client]:
        """if successful, returns clients as data mapped as clientId -> client"""
        pass

    @abstractmethod
    def save_client(
        self,
        client: Client,
    ) -> IntentResult:
        """attempts to create or update a client

        if client passed has id, then it is an update operation
        returns the new /updated client as data if successful
        """
        pass

    @abstractmethod
    def get_client_by_id(self, clientId) -> IntentResult:
        """if successful, returns the client as data"""
        pass

    @abstractmethod
    def get_all_contacts_as_map(
        self,
    ) -> Mapping[int, Contact]:
        """if successful, returns contacts as data mapped as contactId -> contact"""
        pass
