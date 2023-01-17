from typing import Mapping, Type, Union

from core.intent_result import IntentResult
from .data_source import ClientDataSource
from contacts.intent import ContactsIntent
from tuttle.model import Client, Contact


class ClientsIntent:
    """Provides methods to retrieve, store and delete clients from datasources"""

    def __init__(self):
        """
        Attributes
        ----------
        _data_source : ClientDataSource
            reference to the client's data source
        _contacts_intent :  ContactsIntent
            reference to contacts_intent for forwarding Contact related intents
        """
        self._contacts_intent = ContactsIntent()
        self._data_source = ClientDataSource()

    def get_all_clients_as_map(self) -> Mapping[int, Client]:
        """Retrieves all existing clients from the data source and returns them as a map of client IDs to clients

        Returns:
            Mapping[int, Client]: A dictionary containing all clients with their ID as key
        """
        result = self._data_source.get_all_clients()
        if result.was_intent_successful:
            clients = result.data
            clients_map = {client.id: client for client in clients}
            return clients_map
        else:
            result.log_message_if_any()
        return {}

    def save_client(
        self,
        client: Client = None,
    ) -> IntentResult[Union[Type[Client], None]]:
        """Saves a client in the data source

        Args:
            client (Client): The client to save.

        Returns:
            IntentResult[Client]: An object indicating the result of the intent
        """
        if not client.name:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Please provide the client's name",
            )
        if (
            not client.invoicing_contact.first_name
            or not client.invoicing_contact.last_name
        ):
            return IntentResult(
                was_intent_successful=False,
                error_msg="A contact name is required.",
            )
        if client.invoicing_contact.address.is_empty:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Please specify the contact address.",
            )
        result = self._data_source.save_client(
            client=client,
        )

        if not result.was_intent_successful:
            result.log_message_if_any()
            result.error_msg = "Failed to save the client! Please retry"
        return result

    def get_all_contacts_as_map(self) -> Mapping[int, Contact]:
        """Retrieves all existing contacts from the data source and returns them as a map of contact IDs to contacts

        Returns:
            Mapping[int, Contact]: A dictionary containing all contacts with their ID as key
        """
        return self._contacts_intent.get_all_contacts_as_map()

    def delete_client_by_id(self, client_id) -> IntentResult:
        """Deletes a client with the given id from the data source

        Args:
            client_id : The id of the client to delete

        Returns:
            IntentResult: An object indicating the result of the intent
        """
        result: IntentResult = self._data_source.delete_client_by_id(client_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete the client! please retry"
            result.log_message_if_any()
        return result
