from typing import Mapping, Optional
from core.abstractions import LocalCache
from clients.abstractions import ClientsIntent
from clients.utils import ClientIntentsResult
from clients.clients_data_source_impl import ClientDataSourceImpl
from clients.client_model import Client
from res.strings import CREATE_CLIENT_FAILED_ERR, CLIENT_NOT_FOUND


class ClientIntentImpl(ClientsIntent):
    def __init__(self, cache: LocalCache):
        super().__init__(cache=cache, dataSource=ClientDataSourceImpl())
        self.allClientsCache: Mapping[str, Client] = None

    def get_all_clients(self) -> Mapping[str, Client]:
        if self.allClientsCache:
            # return cached results
            return self.allClientsCache

        # fetch from data source
        self._clear_cached_results()
        result = self.dataSource.get_all_clients_as_map()
        if result.wasIntentSuccessful:
            self.allClientsCache = result.data
            return self.allClientsCache
        else:
            # TODO log error
            return {}

    def _clear_cached_results(self):
        self.allClientsCache = None

    def cache_clients_data(self, key: str, data: any):
        self.cache.set_value(key, data)

    def create_or_update_client(
        self, title: str, invoicing_contact_id: Optional[str]
    ) -> ClientIntentsResult:
        result = self.dataSource.save_client(title=title)
        if result.wasIntentSuccessful and invoicing_contact_id:
            self.dataSource.set_client_contact_id(
                invoicing_contact_id=invoicing_contact_id, client_id=result.data
            )
        if not result.wasIntentSuccessful:
            result.errorMsg = CREATE_CLIENT_FAILED_ERR
        return result

    def get_client_by_id(self, clientId) -> ClientIntentsResult:
        clientIfFound = self.dataSource.get_client_by_id(clientId=clientId)
        return ClientIntentsResult(
            wasIntentSuccessful=clientIfFound != None,
            data=clientIfFound,
            errorMsgIfAny=CLIENT_NOT_FOUND if clientIfFound == None else "",
        )

    def set_client_invoicing_contact_id(
        self, invoicing_contact_id: str, client_id: str
    ) -> ClientIntentsResult:
        return self.dataSource.set_client_contact_id(invoicing_contact_id, client_id)
