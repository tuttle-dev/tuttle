from typing import List, Optional, Type, Union

from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult

from tuttle.model import Client


class ClientDataSource(SQLModelDataSourceMixin):
    """Provides methods to retrieve, store and delete clients from the database"""

    def __init__(self):
        super().__init__()

    def get_all_clients(self) -> IntentResult[Union[List[Client], None]]:
        """Retrieves all existing clients from the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : list[Client]  if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            clients = self.query(Client)
            return IntentResult(was_intent_successful=True, data=clients)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ClientDataSource.get_all_clients {e.__class__.__name__}",
                exception=e,
            )

    def save_client(self, client: Client) -> IntentResult[Union[Type[Client], None]]:
        """Stores a client in the database. Used for creating or updating a client's information

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : Client  if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            self.store(client)
            return IntentResult(
                was_intent_successful=True,
                data=client,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ClientDataSource.save_client {e.__class__.__name__}",
                exception=e,
            )

    def delete_client_by_id(self, client_id) -> IntentResult[None]:
        """Attempts to delete a client with the given id from the database

        Args:
            client_id : The id of the client to delete

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        self.delete_by_id(Client, client_id)
