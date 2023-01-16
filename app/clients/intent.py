from typing import Mapping

from core.intent_result import IntentResult
from .data_source import ClientDataSource
from contacts.intent import ContactsIntent
from tuttle.model import (
    Client,
)


class ClientsIntent:
    """Handles Clients C_R_U_D intents

    Intents handled (Methods)
    ---------------

    get_all_clients_as_map_intent
        fetching existing clients as a map of client IDs to clients

    save_client_intent
        saving the client

    get_all_contacts_as_map_intent
        fetching existing contacts as a map of contact IDs to contacts

    delete_client_by_id_intent
        deleting a client given it's id
    """

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
    ) -> IntentResult:
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

    def get_all_contacts_as_map(self) -> IntentResult:
        return self._contacts_intent.get_all_contacts_as_map()

    def delete_client_by_id(self, client_id):
        result: IntentResult = self._data_source.delete_client_by_id(client_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete the client! please retry"
            result.log_message_if_any()
        return result
