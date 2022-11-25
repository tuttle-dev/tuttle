from abc import abstractmethod
from typing import Callable, Mapping, Optional

from flet import UserControl
from core.views.alert_dialog_controls import AlertDialogControls
from core.models import Address
from .contact_model import Contact
from .utils import ContactIntentsResult
from core.abstractions import DataSource, Intent, LocalCache, TuttleDestinationView


class ContactDataSource(DataSource):
    """Defines methods for instantiating, viewing, updating, saving and deleting contacts"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_all_contacts_as_map(
        self,
    ) -> ContactIntentsResult:
        """if successful, returns data as all contacts this user has in a map of contactId - contact"""
        pass

    @abstractmethod
    def save_address(
        self,
        address_id: Optional[int],
        street: str,
        number: str,
        city: str,
        postal_code: str,
        country: str,
    ) -> ContactIntentsResult:
        """attempts to create or update a new address

        returns new/updated address as data if successful
        """
        pass

    @abstractmethod
    def save_contact(
        self,
        contact_id: Optional[int],
        first_name: str,
        last_name: str,
        company: Optional[str],
        email: str,
        address: Optional[Address] = None,
    ) -> ContactIntentsResult:
        """attempts to create or update a new contact

        returns new contact as data if successful
        """
        pass

    @abstractmethod
    def set_contact_address_id(
        self, address_id: str, contact_id: str
    ) -> ContactIntentsResult:
        """sets the address id of a given contact"""
        pass

    @abstractmethod
    def get_contact_by_id(self, contactId) -> ContactIntentsResult:
        """if successful, returns the contact as data"""
        pass

    @abstractmethod
    def get_address_by_id(self, addressId) -> ContactIntentsResult:
        """if successful, returns the address as data"""
        pass

    @abstractmethod
    def create_contact_and_address(self, contact: Contact) -> ContactIntentsResult:
        """attemtpts to save a contact object with it's address

        if successful, returns the newly created contact as data"""
        pass


class ContactsIntent(Intent):
    """Handles contact view intents"""

    def __init__(self, dataSource: ContactDataSource, cache: LocalCache):
        super().__init__(cache=cache, dataSource=dataSource)
        self.cache = cache
        self.dataSource = dataSource

    @abstractmethod
    def get_all_contacts(
        self,
    ) -> Mapping[str, Contact]:
        """fetches all contacts this user has"""
        pass

    @abstractmethod
    def cache_contacts_data(self, key: str, data: any):
        """caches frequently used key-value pairs related to contacts"""
        pass

    @abstractmethod
    def create_contact_and_address(self, contact: Contact) -> ContactIntentsResult:
        """attemtpts to save a contact object with it's address

        if successful, returns the newly created contact as data"""
        pass

    @abstractmethod
    def create_or_update_address(
        self,
        address_id: Optional[int],
        street: str,
        number: str,
        city: str,
        postal_code: str,
        country: str,
    ) -> ContactIntentsResult:
        """attempts to create or update an address

        returns new/updated address as data if successful
        """
        pass

    @abstractmethod
    def create_or_update_contact(
        self,
        contact_id: Optional[str],
        first_name: str,
        last_name: str,
        company: Optional[str],
        email: str,
        address: Optional[Address] = None,
    ) -> ContactIntentsResult:
        """attempts to create or update a contact
        returns the contact as data if successful
        """
        pass

    @abstractmethod
    def set_contact_address_id(
        self, address_id: str, contact_id: str
    ) -> ContactIntentsResult:
        """sets the address id of a given contact"""
        pass

    @abstractmethod
    def get_contact_by_id(self, contactId) -> ContactIntentsResult:
        """if successful, returns the contact as data"""
        pass

    @abstractmethod
    def get_address_by_id(self, addressId) -> ContactIntentsResult:
        """if successful, returns the address as data"""
        pass


class ContactDestinationView(TuttleDestinationView, UserControl):
    """Describes the destination screen that displays all contacts
    initializes the intent handler
    """

    def __init__(
        self,
        intentHandler: ContactsIntent,
        onChangeRouteCallback: Callable[[str, Optional[any]], None],
        pageDialogController: Callable[[any, AlertDialogControls], None],
    ):
        super().__init__(
            intentHandler=intentHandler,
            onChangeRouteCallback=onChangeRouteCallback,
            pageDialogController=pageDialogController,
        )
        self.intentHandler = intentHandler
