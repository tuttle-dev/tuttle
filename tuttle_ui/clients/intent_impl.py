from typing import Optional, Mapping

from core.abstractions import ClientStorage
from core.models import IntentResult
from .client_model import Client
from contacts.contact_model import Contact
from .abstractions import ClientsIntent
from .data_source_impl import ClientDataSourceImpl
from contacts.data_source_impl import ContactDataSourceImpl


class ClientsIntentImpl(ClientsIntent):
    def __init__(self, local_storage: ClientStorage):
        super().__init__(
            data_source=ClientDataSourceImpl(), local_storage=local_storage
        )
        self.contacts_data_source = ContactDataSourceImpl()

    def get_all_clients_as_map(self) -> Mapping[int, Client]:
        try:
            result = self.data_source.get_all_clients_as_map()
            if not result.was_intent_successful:
                return {}
            return result.data
        except Exception as e:
            print(f"Exception raised @clients.intent_impl.get_all_clients_as_map {e}")
            return {}

    def save_client(
        self,
        client: Client = None,
    ) -> IntentResult:
        if not client.title:
            return IntentResult(
                was_intent_successful=False,
                error_msg_if_err="Please provide the client's title",
                data=None,
            )
        if (
            not client.invoicing_contact.first_name
            or not client.invoicing_contact.last_name
        ):
            return IntentResult(
                was_intent_successful=False,
                error_msg_if_err="A contact name is required.",
                data=None,
            )
        if client.invoicing_contact.address.is_empty():
            return IntentResult(
                was_intent_successful=False,
                error_msg_if_err="Please specify the contact address.",
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
        result = self.contacts_data_source.get_all_contacts_as_map()
        if result.was_intent_successful:
            return result.data
        else:
            return {}
