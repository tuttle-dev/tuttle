from typing import Mapping, Optional

import datetime

from clients.intent import ClientsIntent
from contacts.intent import ContactsIntent
from core.abstractions import ClientStorage
from core.intent_result import IntentResult
from preferences.intent import PreferencesIntent
from preferences.model import PreferencesStorageKeys

from tuttle.model import Client, Contact, Contract
from tuttle.time import Cycle, TimeUnit

from .data_source import ContractDataSource


class ContractsIntent:
    """Handles Contract C_R_U_D intents"""

    def __init__(self):
        self._clients_intent = ClientsIntent()
        self._contacts_intent = ContactsIntent()
        self._data_source = ContractDataSource()
        self._all_contracts_cache: Mapping[str, Contract] = None
        self._completed_contracts_cache: Mapping[str, Contract] = None
        self._active_contracts_cache: Mapping[str, Contract] = None
        self._upcoming_contracts_cache: Mapping[str, Contract] = None

    def get_preferred_currency_intent(
        self, client_storage: ClientStorage
    ) -> IntentResult:
        """
        Retrieves the preferred currency of the client from the local storage

        Parameters:
        client_storage (ClientStorage): The client storage object from which the preferred currency is retrieved

        Returns:
        IntentResult : An intent result object indicating the success or failure of the operation
        """
        _preferences_intent = PreferencesIntent(client_storage=client_storage)
        return _preferences_intent.get_preference_by_key(
            preference_key=PreferencesStorageKeys.default_currency_key
        )

    def get_contract_by_id(self, contractId) -> IntentResult:
        """
        Retrieves a contract by its id

        Parameters:
        contractId (str): The id of the contract to retrieve

        Returns:
        IntentResult : An intent result object indicating the success or failure of the operation and the contract details if successful
        """
        result = self._data_source.get_contract_by_id(contractId)
        if not result.was_intent_successful:
            result.error_msg = "Failed to load contract details. Please retry"
            result.log_message_if_any()
        return result

    def get_all_clients_as_map(self) -> Mapping[int, Client]:
        """
        Retrieves all clients as a map

        Returns:
        Mapping[int, Client] : A map containing all clients"""
        return self._clients_intent.get_all_clients_as_map()

    def get_all_contacts_as_map(self) -> Mapping[int, Contact]:
        """
        Retrieves all contacts as a map

        Returns:
        Mapping[int, Contact] : A map containing all contacts
        """
        return self._contacts_intent.get_all_contacts_as_map()

    def save_client(self, client: Client) -> IntentResult:
        """
        Saves a client

        Parameters:
        client (Client): The client object to save

        Returns:
        IntentResult : An intent result object indicating the success or failure of the operation
        """
        return self._clients_intent.save_client(client=client)

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
        contract_to_update: Optional[Contract] = None,
    ) -> IntentResult:
        """Saves or updates a contract

        Parameters:
            title (str) : The title of the contract
            signature_date (datetime.date) : The date the contract was signed
            start_date (datetime.date) : The start date of the contract
            end_date (Optional[datetime.date]) : The end date of the contract
            client (Client) : The client associated with the contract
            rate (str) : The rate of the contract
            currency (str) : The currency of the contract
            VAT_rate (str) : The VAT rate of the contract
            unit (TimeUnit) : The unit of time for the contract
            units_per_workday (str) : The number of units per workday
            volume (Optional[str]) : The volume of the contract
            term_of_payment (Optional[str]) : The term of payment for the contract
            billing_cycle (Cycle) : The billing cycle for the contract (defaults to Cycle.hourly)
            is_completed (bool) : Whether the contract is completed or not (defaults to False)
            contract_to_update (Optional[Contract]) : The contract to update (if updating an existing contract)

        Returns:
        IntentResult : An intent result object indicating the success or failure of the operation

        """
        result: IntentResult = self._data_source.save_or_update_contract(
            title=title,
            signature_date=signature_date,
            start_date=start_date,
            end_date=end_date,
            client=client,
            rate=rate,
            currency=currency,
            VAT_rate=VAT_rate,
            unit=unit,
            units_per_workday=units_per_workday,
            volume=volume,
            term_of_payment=term_of_payment,
            billing_cycle=billing_cycle,
            is_completed=is_completed,
            contract=contract_to_update,
        )
        if not result.was_intent_successful:
            result.error_msg = "Failed to save the contract. Verify the info and retry."
            result.log_message_if_any()
        return result

    def get_all_contracts_as_map(
        self, reload_cache: bool = False
    ) -> Mapping[int, Contract]:
        """Retrieves all completed contracts as a map

        Parameters:
        reload_cache (bool) : Whether to reload the cache or use the existing one (defaults to False)

        Returns:
        Mapping[str, Contract] : A map containing all completed contracts in the system
        """
        if self._all_contracts_cache and not reload_cache:
            # return cached results
            return self._all_contracts_cache
        self._clear_cached_results()
        result = self._data_source.get_all_contracts()
        if result.was_intent_successful:
            contracts = result.data
            contracts_map = {contract.id: contract for contract in contracts}
            self._all_contracts_cache = contracts_map
        else:
            result.log_message_if_any()
            self._all_contracts_cache = {}
        return self._all_contracts_cache

    def get_completed_contracts(self) -> Mapping[str, Contract]:
        if not self._all_contracts_cache:
            self.get_all_contracts_as_map()
        if not self._completed_contracts_cache:
            self._completed_contracts_cache = {}
            for key in self._all_contracts_cache:
                c = self._all_contracts_cache[key]
                if c.is_completed:
                    self._completed_contracts_cache[key] = c
        return self._completed_contracts_cache

    def get_active_contracts(self):
        if not self._all_contracts_cache:
            self.get_all_contracts_as_map()
        if not self._active_contracts_cache:
            self._active_contracts_cache = {}
            for key in self._all_contracts_cache:
                c = self._all_contracts_cache[key]
                if c.is_active():
                    self._active_contracts_cache[key] = c
        return self._active_contracts_cache

    def get_upcoming_contracts(self):
        if not self._all_contracts_cache:
            self.get_all_contracts_as_map()
        if not self._upcoming_contracts_cache:
            self._upcoming_contracts_cache = {}
            for key in self._all_contracts_cache:
                c = self._all_contracts_cache[key]
                if c.is_upcoming():
                    self._upcoming_contracts_cache[key] = c
        return self._upcoming_contracts_cache

    def delete_contract_by_id(self, contract_id: str):
        result: IntentResult = self._data_source.delete_contract_by_id(contract_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete that contract! Please retry"
            result.log_message_if_any()
        else:
            self._remove_contract_from_cache(contract_id)
        return result

    def _remove_contract_from_cache(self, contract_id: str):
        if self._all_contracts_cache and contract_id in self._all_contracts_cache:
            del self._all_contracts_cache[contract_id]

        if (
            self._completed_contracts_cache
            and contract_id in self._completed_contracts_cache
        ):
            del self._completed_contracts_cache[contract_id]

        if self._active_contracts_cache and contract_id in self._active_contracts_cache:
            del self._active_contracts_cache[contract_id]

        if (
            self._upcoming_contracts_cache
            and contract_id in self._upcoming_contracts_cache
        ):
            del self._upcoming_contracts_cache[contract_id]

    def _clear_cached_results(self):
        self._all_contracts_cache = None
        self._completed_contracts_cache = None
        self._active_contracts_cache = None
        self._upcoming_contracts_cache = None
