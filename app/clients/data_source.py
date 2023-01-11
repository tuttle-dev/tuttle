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

    def get_all_clients_as_map(self) -> IntentResult:
        clients = self.query(Client)
        result = {client.id: client for client in clients}
        return IntentResult(
            was_intent_successful=True,
            data=result,
        )

    def save_client(self, client: Client) -> IntentResult:
        self.store(client)
        logger.info(f"Saved Client: {client}")
        return IntentResult(
            was_intent_successful=True,
            data=client,
        )
