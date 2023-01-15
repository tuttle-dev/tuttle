import datetime

from typing import Optional, Mapping
from core.models import Cycle, TimeUnit


from core.intent_result import IntentResult

from .data_source import ContractDataSource
from clients.intent import ClientsIntent
from contacts.intent import ContactsIntent

from tuttle.model import (
    Client,
    Contract,
    Contact,
)


class ContractsIntent:
    """Handles Contract C_R_U_D intents

    Intents handled (Methods)
    ---------------
    get_contract_by_id_intent
        reading a contract info given it's id

    get_all_clients_as_map_intent
        fetching existing clients as a map of client IDs to client

    get_all_contacts_as_map_intent
        fetching existing contacts as a map of contact IDs to contact

    save_client_intent
        saving a client -- forwards to Client's intent

    get_upcoming_contracts_intent
        fetching upcoming contracts as a map of contract IDs to contract

    get_completed_contracts_intent
        fetching completed contracts as a map of contract IDs to contract

    get_active_contracts_intent
        fetching active contracts as a map of contract IDs to contract

    get_all_contracts_as_map_intent
        fetching existing contracts as a map of contract IDs to contract

    save_contract_intent
        saving the contract

    delete_contract_by_id_intent
        deleting a contract given it's id
    """

    def __init__(
        self,
    ):
        """
        Attributes
        ----------
        _data_source : ContractDataSource
            reference to the contract's data source
        _clients_intent :  ClientsIntent
            reference to the client's Intent handler for forwarding client related intents
        _contacts_intent  : ContactsIntent
            reference to the contact's Intent handler for forwarding contact related intents
        _all_contracts_cache : Mapping[str, Contract]
            caches fetched contracts to reduce unnecessary database calls
        _completed_contracts_cache : Mapping[str, Contract]
            caches completed contracts to reduce unnecessary database calls
        _active_contracts_cache  :   Mapping[str, Contract]
            caches active contracts to reduce unnecessary database calls
        _upcoming_contracts_cache : Mapping[str, Contract]
            caches upcoming contracts to reduce unnecessary database calls
        """
        self._clients_intent = ClientsIntent()
        self._contacts_intent = ContactsIntent()
        self._data_source = ContractDataSource()
        self._all_contracts_cache: Mapping[str, Contract] = None
        self._completed_contracts_cache: Mapping[str, Contract] = None
        self._active_contracts_cache: Mapping[str, Contract] = None
        self._upcoming_contracts_cache: Mapping[str, Contract] = None

    def get_contract_by_id(self, contractId) -> IntentResult:
        result = self._data_source.get_contract_by_id(contractId)
        if not result.was_intent_successful:
            result.error_msg = "Failed to load contract details. Please retry"
            result.log_message_if_any()
        return result

    def get_all_clients_as_map(self) -> Mapping[int, Client]:
        return self._clients_intent.get_all_clients_as_map()

    def get_all_contacts_as_map(self) -> Mapping[int, Contact]:
        return self._contacts_intent.get_all_contacts_as_map()

    def save_client(self, client: Client) -> IntentResult:
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
        if contract_to_update:
            _id = contract_to_update.id
        else:
            _id = None
        contract = Contract(
            id=_id,
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
        )

        return self._data_source.save_contract(contract=contract)

    def get_all_contracts_as_map(self) -> Mapping[int, Contract]:
        if self._all_contracts_cache:
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
