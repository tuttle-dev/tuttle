from abc import abstractmethod
from typing import Callable, Mapping, Optional

from flet import UserControl

from .client_model import Client
from .utils import ClientIntentsResult
from core.abstractions import DataSource, Intent, LocalCache, TuttleDestinationView


class ClientDataSource(DataSource):
    """Defines methods for instantiating, viewing, updating, saving and deleting clients"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_all_clients_as_map(
        self,
    ) -> ClientIntentsResult:
        """if successful, returns data as all clients this user has in a map of clientId - client"""
        pass

    @abstractmethod
    def create_client(
        self,
        title: str,
    ) -> ClientIntentsResult:
        """attempts to create a new client

        returns new client as data if successful
        """
        pass

    def update_client(self, client: Client) -> ClientIntentsResult:
        """attempts to update a client, if successful returns updated client as data"""
        pass

    @abstractmethod
    def set_client_contact_id(
        self, invoicing_contact_id: str, client_id: str
    ) -> ClientIntentsResult:
        """sets the contact id of a given client"""
        pass

    @abstractmethod
    def get_client_by_id(self, clientId) -> ClientIntentsResult:
        """if successful, returns the client as data"""
        pass


class ClientsIntent(Intent):
    """Handles client view intents"""

    def __init__(self, dataSource: ClientDataSource, cache: LocalCache):
        super().__init__(cache=cache, dataSource=dataSource)
        self.cache = cache
        self.dataSource = dataSource

    @abstractmethod
    def get_all_clients(
        self,
    ) -> Mapping[str, Client]:
        """fetches all clients this user has"""
        pass

    @abstractmethod
    def cache_clients_data(self, key: str, data: any):
        """caches frequently used key-value pairs related to clients"""
        pass

    @abstractmethod
    def create_client(self, title: str) -> ClientIntentsResult:
        """attempts to create a new client

        returns the client as data if intent is successful
        """
        pass

    @abstractmethod
    def set_client_invoicing_contact_id(
        self, invoicing_contact_id: str, client_id: str
    ) -> ClientIntentsResult:
        """sets the contact id of a given client"""
        pass

    @abstractmethod
    def get_client_by_id(self, clientId) -> ClientIntentsResult:
        """if successful, returns the client as data"""
        pass

    @abstractmethod
    def get_all_contacts_as_map(self) -> ClientIntentsResult:
        """if successful, returns data as all contacts this user has in a map of contactId - contact"""
        pass

    def update_client(self, client: Client) -> ClientIntentsResult:
        """attempts to update a client, if successful returns updated client as data"""
        pass


class ClientDestinationView(TuttleDestinationView, UserControl):
    """Describes the destination screen that displays all clients
    initializes the intent handler
    """

    def __init__(
        self,
        intentHandler: ClientsIntent,
        onChangeRouteCallback: Callable[[str, Optional[any]], None],
    ):
        super().__init__(
            intentHandler=intentHandler, onChangeRouteCallback=onChangeRouteCallback
        )
        self.intentHandler = intentHandler
