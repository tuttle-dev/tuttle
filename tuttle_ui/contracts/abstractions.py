import datetime

from abc import ABC, abstractmethod
from typing import Optional, Mapping
from pydantic import condecimal
from decimal import Decimal
from core.models import Cycle, TimeUnit


from clients.client_model import Client
from core.abstractions import ClientStorage
from core.models import IntentResult

from .contract_model import Contract


class ContractDataSource(ABC):
    """Defines methods for instantiating, viewing, updating, saving and deleting contracts"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_all_contracts_as_map(
        self,
    ) -> IntentResult:
        """if successful, returns contracts as data mapped as contractId -> contract"""
        pass

    @abstractmethod
    def save_contract(
        self,
        title: str,
        signature_date: datetime.date,
        start_date: datetime.date,
        end_date: Optional[datetime.date],
        client: Client,
        rate: condecimal(decimal_places=2),
        currency: str,
        VAT_rate: Decimal,
        unit: TimeUnit,
        units_per_workday: int,
        volume: Optional[int],
        term_of_payment: Optional[int],
        billing_cycle: Cycle = Cycle.hourly,
        is_completed: bool = False,
        contract: Optional[Contract] = None,
    ) -> IntentResult:
        """attempts to create or update a contract

        if contract is passed, then it is an update operation
        returns the new /updated contract as data if successful
        """
        pass

    @abstractmethod
    def get_contract_by_id(self, contractId) -> IntentResult:
        """if successful, returns the contract as data"""
        pass


class ContractsIntent(ABC):
    """Handles contract view intents"""

    def __init__(self, data_source: ContractDataSource, local_storage: ClientStorage):
        super().__init__()
        self.local_storage = local_storage
        self.data_source = data_source

    @abstractmethod
    def get_all_contracts_as_map(
        self,
    ) -> Mapping[int, Contract]:
        """if successful, returns contracts as data mapped as contractId -> contract"""
        pass

    @abstractmethod
    def save_contract(
        self,
        title: str,
        signature_date: datetime.date,
        start_date: datetime.date,
        end_date: Optional[datetime.date],
        client: Client,
        rate: str,
        currency: str,
        VAT_rate: str,
        unit: TimeUnit,
        units_per_workday: str,
        volume: Optional[str],
        term_of_payment: Optional[str],
        billing_cycle: Cycle = Cycle.hourly,
        is_completed: bool = False,
        contract: Optional[Contract] = None,
    ) -> IntentResult:
        """attempts to create or update a contract

        if contract is passed, then it is an update operation
        returns the new /updated contract as data if successful
        """
        pass

    @abstractmethod
    def get_contract_by_id(self, contractId) -> IntentResult:
        """if successful, returns the contract as data"""
        pass

    @abstractmethod
    def get_all_clients_as_map(
        self,
    ) -> Mapping[int, Client]:
        """if successful, returns clients as data mapped as clientId -> client"""
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
