import datetime
from abc import abstractmethod
from decimal import Decimal
from typing import Callable, Mapping, Optional

from flet import UserControl
from pydantic import condecimal

from contracts.contract_model import Contract
from contracts.utils import ContractIntentsResult
from core.abstractions import DataSource, Intent, LocalCache, TuttleDestinationView

from core.models import Cycle, TimeUnit


class ContractDataSource(DataSource):
    """Defines methods for instantiating, viewing, updating, saving and deleting contracts"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_all_contracts_as_map(
        self,
    ) -> ContractIntentsResult:
        """if successful, returns data as all contracts this user has in a map of contractId - contract"""
        pass

    @abstractmethod
    def save_contract(
        self,
        title: str,
        signature_date: datetime.date,
        start_date: datetime.date,
        end_date: datetime.date,
        client_id: int,
        rate: condecimal(decimal_places=2),
        currency: str,
        VAT_rate: Decimal,
        unit: TimeUnit,
        units_per_workday: int,
        volume: int,
        term_of_payment: int,
        billing_cycle: Cycle,
    ) -> ContractIntentsResult:
        """attempts to create a new contract

        returns new contract id as data if successful
        """
        pass

    @abstractmethod
    def get_contract_by_id(self, contractId) -> ContractIntentsResult:
        """if successful, returns the contract as data"""
        pass


class ContractsIntent(Intent):
    """Handles contract view intents"""

    def __init__(self, dataSource: ContractDataSource, cache: LocalCache):
        super().__init__(cache=cache, dataSource=dataSource)
        self.cache = cache
        self.dataSource = dataSource

    @abstractmethod
    def get_all_contracts(
        self,
    ) -> Mapping[str, Contract]:
        """fetches all contracts this user has"""
        pass

    @abstractmethod
    def get_completed_contracts(self) -> Mapping[str, Contract]:
        """filters contracts to display only completed contracts"""
        pass

    @abstractmethod
    def get_active_contracts(self) -> Mapping[str, Contract]:
        """filters contracts to display only active contracts"""
        pass

    @abstractmethod
    def get_upcoming_contracts(self) -> Mapping[str, Contract]:
        """filters contracts to display only upcoming contracts"""
        pass

    @abstractmethod
    def cache_contracts_data(self, key: str, data: any):
        """caches frequently used key-value pairs related to contracts"""
        pass

    @abstractmethod
    def create_or_update_contract(
        self,
        title: str,
        signature_date: datetime.date,
        start_date: datetime.date,
        end_date: datetime.date,
        client_id: int,
        rate: condecimal(decimal_places=2),
        currency: str,
        VAT_rate: Decimal,
        unit: TimeUnit,
        units_per_workday: int,
        volume: int,
        term_of_payment: int,
        billing_cycle: Cycle,
    ) -> ContractIntentsResult:
        """attempts to create a new contract

        returns new contract id as data if intent is successful
        """
        pass

    @abstractmethod
    def get_contract_by_id(self, contractId) -> ContractIntentsResult:
        """if successful, returns the contract as data"""
        pass


class ContractDestinationView(TuttleDestinationView, UserControl):
    """Describes the destination screen that displays all contracts
    initializes the intent handler
    """

    def __init__(
        self,
        intentHandler: ContractsIntent,
        onChangeRouteCallback: Callable[[str, Optional[any]], None],
    ):
        super().__init__(
            intentHandler=intentHandler, onChangeRouteCallback=onChangeRouteCallback
        )
        self.intentHandler = intentHandler
