from core.intent_result import IntentResult
from core.abstractions import SQLModelDataSourceMixin
from tuttle.model import (
    Client,
)


class ClientDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the Client model in the database"""

    def __init__(self):
        super().__init__()

    def get_all_clients(self) -> IntentResult:
        """Gets all existing clients

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : list[User]  if was_intent_successful else None
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

    def save_client(self, client: Client) -> IntentResult:
        """Stores a client. Used for creation of or to update a client info

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

    def delete_client_by_id(self, client_id):
        """Attempts to delete the client with the given id

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            self.delete_by_id(Client, client_id)
            return IntentResult(was_intent_successful=True)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ClientDataSource.delete_client_by_id {e.__class__.__name__}",
                exception=e,
            )
