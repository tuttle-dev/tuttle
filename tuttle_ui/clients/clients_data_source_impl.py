import faker

from .abstractions import ClientDataSource
from .client_model import Client, create_client_from_title
from .utils import ClientIntentsResult
from typing import Mapping

# TODO
class ClientDataSourceImpl(ClientDataSource):
    def __init__(self):
        super().__init__()
        self.clients: Mapping[str, Client] = {}

    def get_all_clients_as_map(
        self,
    ) -> ClientIntentsResult:
        self._set_dummy_clients()
        return ClientIntentsResult(wasIntentSuccessful=True, data=self.clients)

    def update_client(self, client: Client):
        return ClientIntentsResult(wasIntentSuccessful=True, data=client)

    def create_client(self, title: str) -> ClientIntentsResult:
        client = create_client_from_title(title)
        return ClientIntentsResult(wasIntentSuccessful=True, data=client)

    def set_client_contact_id(
        self, invoicing_contact_id: str, client_id: str
    ) -> ClientIntentsResult:
        return ClientIntentsResult(wasIntentSuccessful=True)

    def get_client_by_id(self, clientId) -> ClientIntentsResult:
        i = int(clientId)
        c = Client(id=i, title=f"Client {i}")
        return ClientIntentsResult(wasIntentSuccessful=True, data=c)

    """DUMMY CONTENT BELOW ---  DELETE ALL"""

    def _set_dummy_clients(self):
        fake = faker.Faker(
            ["fr_FR", "en_US", "de_DE", "es_ES", "it_IT", "sv_SE", "zh_CN"]
        )

        self.clients.clear()
        total = 16
        for i in range(total):
            c = Client(id=i, title=fake.company(), invoicing_contact_id=int(i * 3.142))
            self.clients[c.id] = c
