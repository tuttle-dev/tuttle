from typing import Mapping, Optional
from core.models import Cycle, TimeUnit
from core.abstractions import LocalCache
from contracts.abstractions import ContractsIntent
from contracts.utils import ContractIntentsResult
from contracts.contracts_data_source_impl import ContractDataSourceImpl
from contracts.contract_model import Contract
from res.strings import (
    CREATE_CONTRACT_FAILED_ERR,
    CONTRACT_NOT_FOUND,
    CREATE_CLIENT_FAILED_ERR,
)
import datetime


class ContractIntentImpl(ContractsIntent):
    def __init__(self, cache: LocalCache):
        super().__init__(cache=cache, dataSource=ContractDataSourceImpl())
        self.allContractsCache: Mapping[str, Contract] = None
        self.completedContractsCache: Mapping[str, Contract] = None
        self.activeContractsCache: Mapping[str, Contract] = None
        self.upcomingContractsCache: Mapping[str, Contract] = None

    def get_all_contracts(self) -> Mapping[str, Contract]:
        if self.allContractsCache:
            # return cached results
            return self.allContractsCache

        # fetch from data source
        self._clear_cached_results()
        result = self.dataSource.get_all_contracts_as_map()
        if result.wasIntentSuccessful:
            self.allContractsCache = result.data
            return self.allContractsCache
        else:
            # TODO log error
            return {}

    def get_completed_contracts(self) -> Mapping[str, Contract]:
        if not self.completedContractsCache:
            self.completedContractsCache = {}
            for key in self.allContractsCache:
                c = self.allContractsCache[key]
                if c.is_completed:
                    self.completedContractsCache[key] = c
        return self.completedContractsCache

    def get_active_contracts(self):
        if not self.activeContractsCache:
            self.activeContractsCache = {}
            for key in self.allContractsCache:
                c = self.allContractsCache[key]
                if c.is_active():
                    self.activeContractsCache[key] = c
        return self.activeContractsCache

    def get_upcoming_contracts(self):
        if not self.upcomingContractsCache:
            self.upcomingContractsCache = {}
            for key in self.allContractsCache:
                c = self.allContractsCache[key]
                if c.is_upcoming():
                    self.upcomingContractsCache[key] = c
        return self.upcomingContractsCache

    def _clear_cached_results(self):
        self.allContractsCache = None
        self.completedContractsCache = None
        self.activeContractsCache = None
        self.upcomingContractsCache = None

    def cache_contracts_data(self, key: str, data: any):
        self.cache.set_value(key, data)

    def create_or_update_contract(
        self,
        title: str,
        signature_date: datetime.date,
        start_date: datetime.date,
        end_date: datetime.date,
        client_id: int,
        rate: Optional[str],
        currency: Optional[str],
        VAT_rate: Optional[str],
        unit: Optional[TimeUnit],
        units_per_workday: Optional[str],
        volume: Optional[str],
        term_of_payment: Optional[str],
        billing_cycle: Optional[Cycle],
    ) -> ContractIntentsResult:
        result = self.dataSource.save_contract(
            title=title,
            signature_date=signature_date,
            start_date=start_date,
            end_date=end_date,
            client_id=client_id,
            rate=rate,
            currency=currency,
            VAT_rate=VAT_rate,
            unit=unit,
            units_per_workday=units_per_workday,
            volume=volume,
            term_of_payment=term_of_payment,
            billing_cycle=billing_cycle,
        )
        if not result.wasIntentSuccessful:
            result.errorMsg = CREATE_CONTRACT_FAILED_ERR
        return result

    def get_contract_by_id(self, contractId) -> ContractIntentsResult:
        contractIfFound = self.dataSource.get_contract_by_id(contractId=contractId)
        return ContractIntentsResult(
            wasIntentSuccessful=contractIfFound != None,
            data=contractIfFound,
            errorMsgIfAny=CONTRACT_NOT_FOUND if contractIfFound == None else "",
        )

    def create_client(self, title: str) -> ContractIntentsResult:
        result = self.dataSource.create_client(title)
        if not result.wasIntentSuccessful:
            result.errorMsg = CREATE_CLIENT_FAILED_ERR
        return result

    def get_all_clients_as_map(self):
        result = self.dataSource.get_all_clients_as_map()
        idClientMap = {}
        if len(result) > 0:
            for key in result:
                item = result[key]
                idClientMap[key] = item.title
        return idClientMap
