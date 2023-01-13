from typing import Mapping

from core.intent_result import IntentResult
from .data_source import ClientDataSource
from contacts.intent import ContactsIntent
from tuttle.model import (
    Client,
)


class ClientsIntent:
    def __init__(self):
        self.contacts_intent = ContactsIntent()
        self.data_source = ClientDataSource()

    def get_all_clients_as_map(self) -> Mapping[int, Client]:
        try:
            result = self.data_source.get_all_clients()
            if result.was_intent_successful:
                clients = result.data
                clients_map = {client.id: client for client in clients}
                return clients_map
            return {}
        except Exception as e:
            print(
                f"Exception raised @clients.intent_impl.get_all_clients_as_map {e.__class__.__name__}"
            )
            return {}

    def save_client(
        self,
        client: Client = None,
    ) -> IntentResult:
        if not client.name:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Please provide the client's title",
                data=None,
            )
        if (
            not client.invoicing_contact.first_name
            or not client.invoicing_contact.last_name
        ):
            return IntentResult(
                was_intent_successful=False,
                error_msg="A contact name is required.",
                data=None,
            )
        if client.invoicing_contact.address.is_empty:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Please specify the contact address.",
                data=None,
            )
        return self.data_source.save_client(
            client=client,
        )

    def get_client_by_id(self, clientId) -> IntentResult:
        result = self.data_source.get_client_by_id(clientId)
        if not result.was_intent_successful:
            result.error_msg = "--TODO-- error message"
        return result

    def get_all_contacts_as_map(self) -> IntentResult:
        return self.contacts_intent.get_all_contacts_as_map()

    def delete_client_by_id(self, client_id):
        result: IntentResult = self.data_source.delete_client_by_id(client_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete the client! please retry"
        return result
