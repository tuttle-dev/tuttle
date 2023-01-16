from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult
from tuttle.model import Contract, Client
import datetime
from typing import Optional, Mapping
from tuttle.time import Cycle, TimeUnit


class ContractDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the Contract model in the database"""

    def __init__(self):
        super().__init__()

    def get_all_contracts(self) -> IntentResult:
        """Fetches all existing contracts from the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  list[Contract] if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            contracts = self.query(Contract)
            return IntentResult(was_intent_successful=True, data=contracts)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContractDataSource.get_all_contracts {e.__class__.__name__}",
                exception=e,
            )

    def get_contract_by_id(self, contract_id: str) -> IntentResult:
        """Fetches a contract with the contract id if one exists

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  Contract or None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            contract = self.query_by_id(Contract, contract_id)
            return IntentResult(was_intent_successful=True, data=contract)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContractDataSource.get_contract_by_id {e.__class__.__name__}",
                exception=e,
            )

    def save_or_update_contract(
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
        """Creates or updates a contract in the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  Contract if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            if not contract:
                # Create a new contract
                contract = Contract()
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
            self.store(contract)
            return IntentResult(
                was_intent_successful=True,
                data=contract,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContractDataSource.save_contract {e.__class__.__name__}",
                exception=e,
            )

    def delete_contract_by_id(self, contract_id):
        """Attempts to delete the contract associated with the given id
        Returns:
            IntentResult:
                was_intent_successful : bool
                data : None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            self.delete_by_id(Contract, contract_id)
            return IntentResult(was_intent_successful=True)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContractDataSource.delete_contract_by_id {e.__class__.__name__}",
                exception=e,
            )
