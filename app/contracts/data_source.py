from loguru import logger

from core.abstractions import SQLModelDataSourceMixin
from core.models import IntentResult
from tuttle.model import (
    Contract,
)


class ContractDataSource(SQLModelDataSourceMixin):
    """This class provides the data source for the Contract model"""

    def __init__(self):
        """Initialize the ContractDataSource object"""
        super().__init__()

    def get_all_contracts(self) -> IntentResult:
        """Return data as all contracts."""
        try:
            contracts = self.query(Contract)
            return IntentResult(was_intent_successful=True, data=contracts)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContractDataSource.get_all_contracts {e}",
            )

    def get_contract_by_id(self, contractId: str) -> IntentResult:
        """Retrieve a contract by its id.

        Args:
            contractId (str): The id of the contract to be retrieved

        Returns:
            IntentResult : A IntentResult object representing the outcome of the operation
        """
        contract = self.query(Contract).where(id=contractId).first()
        return IntentResult(was_intent_successful=True, data=contract)

    def save_contract(self, contract: Contract) -> IntentResult:
        """Store a contract in the data source.

        Args:
            contract (Contract): the contract to be stored

        Returns:
            IntentResult : A IntentResult object representing the outcome of the operation
        """
        self.store(contract)
        logger.info(f"Saved contract: {contract}")
        return IntentResult(
            was_intent_successful=True,
            data=contract,
        )

    def delete_contract_by_id(self, contract_id):
        """Attempts to delete the contract associated with the given id"""
        try:
            # TODO perform deletion
            return IntentResult(was_intent_successful=True)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"An exception was raised @ContractDataSource.delete_contract_by_id {e}",
            )
