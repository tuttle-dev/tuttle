from typing import Mapping, Optional

import datetime

from ..clients.intent import ClientsIntent
from ..contacts.intent import ContactsIntent
from ..core.abstractions import ClientStorage, Intent
from ..core.intent_result import IntentResult
from ..preferences.intent import PreferencesIntent
from ..preferences.model import PreferencesStorageKeys

from ...model import Client, Contact, Contract
from ...time import Cycle, TimeUnit

from .data_source import ContractDataSource


class ContractsIntent:
    """Handles Contract C_R_U_D intents"""

    def __init__(self):
        self._clients_intent = ClientsIntent()
        self._contacts_intent = ContactsIntent()
        self._data_source = ContractDataSource()

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

    def get_contract_by_id(self, contractId) -> IntentResult[Optional[Contract]]:
        """
        Retrieves a contract by its id

        Parameters:
        contractId : The id of the contract to retrieve

        Returns:
        IntentResult : An intent result object indicating the success or failure of the operation and the contract details if successful
        """
        result = self._data_source.get_contract_by_id(contractId)
        if not result.was_intent_successful:
            result.error_msg = "Failed to load contract details. "
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
        contract: Optional[Contract] = None,
    ) -> IntentResult:
        """Creates a new contract or updates the given contract

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
        is_updating = True
        if not contract:
            # Create a new contract
            contract = Contract()
            is_updating = False
        contract.title = title
        contract.signature_date = signature_date
        contract.start_date = start_date
        contract.end_date = end_date
        contract.client = client
        contract.rate = rate
        contract.currency = currency
        contract.VAT_rate = VAT_rate
        contract.unit = unit
        contract.units_per_workday = units_per_workday
        contract.volume = volume
        contract.term_of_payment = term_of_payment
        contract.billing_cycle = billing_cycle
        contract.is_completed = is_completed
        result: IntentResult = self._data_source.save_contract(
            contract=contract,
        )
        if not result.was_intent_successful:
            if is_updating:
                # recover old contract state
                old_contract_result: IntentResult = self.get_contract_by_id(contract.id)
                result.data = (
                    old_contract_result.data
                    if old_contract_result.was_intent_successful
                    else None
                )
            result.error_msg = "Failed to save the contract. Verify the info and retry."
            result.log_message_if_any()
        return result

    def get_all_contracts_as_map(self) -> Mapping[int, Contract]:
        """Retrieves all completed contracts as a map"""
        result = self._data_source.get_all_contracts()
        if result.was_intent_successful:
            contracts = result.data
            contracts_map = {contract.id: contract for contract in contracts}
            return contracts_map
        else:
            result.log_message_if_any()
            return {}

    def get_completed_contracts(self) -> Mapping[int, Contract]:
        """Retrieves all completed contracts as a map"""
        _all_contracts = self.get_all_contracts_as_map()
        _completed_contracts = {}
        for key in _all_contracts:
            c = _all_contracts[key]
            if c.is_completed:
                _completed_contracts[key] = c
        return _completed_contracts

    def get_active_contracts(self):
        """Retrieves all active contracts as a map"""
        _all_contracts = self.get_all_contracts_as_map()
        _active_contracts = {}
        for key in _all_contracts:
            c = _all_contracts[key]
            if c.is_active():
                _active_contracts[key] = c
        return _active_contracts

    def get_upcoming_contracts(self):
        """Retrieves all upcoming contracts as a map"""
        _all_contracts = self.get_all_contracts_as_map()
        _upcoming_contracts = {}
        for key in _all_contracts:
            c = _all_contracts[key]
            if c.is_upcoming():
                _upcoming_contracts[key] = c
        return _upcoming_contracts

    def delete_contract_by_id(self, contract_id: str):
        """Deletes the contract with the given id"""
        result: IntentResult = self._data_source.delete_contract_by_id(contract_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete that contract! "
            result.log_message_if_any()
        return result

    def toggle_complete_status(self, contract: Contract) -> IntentResult[Contract]:
        """Toggles the completed status of the contract with the given id"""
        contract.is_completed = not contract.is_completed
        result: IntentResult = self._data_source.save_contract(contract=contract)
        if not result.was_intent_successful:
            # undo the change
            contract.is_completed = not contract.is_completed
            result.error_msg = "Failed to update the completed status of the contract. "
            result.log_message_if_any()
        result.data = contract
        return result
