from typing import List, Optional, Union

import datetime

from ..core.abstractions import SQLModelDataSourceMixin
from ..core.intent_result import IntentResult

from ...model import Client, Contract
from ...time import Cycle, TimeUnit


class ContractDataSource(SQLModelDataSourceMixin):
    """Provides methods for fetching, creating, updating and deleting contracts in the database."""

    def __init__(self):
        super().__init__()

    def get_all_contracts(self) -> IntentResult[Union[List[Contract], None]]:
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

    def get_contract_by_id(self, contract_id) -> IntentResult[Union[Contract, None]]:
        """Fetches a contract with the contract id if one exists

        Args:
            contract_id : the id of the contract to fetch

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

    def save_contract(
        self,
        contract: Contract,
    ) -> IntentResult[Optional[Contract]]:
        """Creates or updates a contract in the database

        Args:
            contract Contract: The contract to save

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  Contract if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """

        try:
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

    def delete_contract_by_id(self, contract_id) -> IntentResult[None]:
        """Deletes a contract with the contract id if one exists

        Args:
            contract_id : the id of the contract to delete

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
