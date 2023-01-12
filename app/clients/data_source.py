from typing import Optional

from loguru import logger

from core.models import IntentResult
from core.abstractions import SQLModelDataSourceMixin
from tuttle.model import (
    Client,
)
from tuttle.dev import deprecated


class ClientDataSource(SQLModelDataSourceMixin):
    def __init__(self):
        super().__init__()

    @deprecated
    def get_client_by_id(self, clientId) -> IntentResult:
        raise NotImplementedError("This method is deprecated.")

    def get_all_clients(self) -> IntentResult:
        """returns data as all existing clients"""
        try:
            clients = self.query(Client)
            return IntentResult(was_intent_successful=True, data=clients)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ClientDataSource.get_all_clients {e}",
            )

    def save_client(self, client: Client) -> IntentResult:
        self.store(client)
        logger.info(f"Saved Client: {client}")
        return IntentResult(
            was_intent_successful=True,
            data=client,
        )

    def delete_client_by_id(self, client_id):
        """Attempts to delete the client associated with the given id"""
        try:
            # TODO perform deletion
            return IntentResult(was_intent_successful=True)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ClientDataSource.delete_client_by_id {e}",
            )
