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

    def get_all_contracts_as_map(self) -> IntentResult:
        """Retrieve all contracts and return them as a map with the contract's id as the key.

        Returns:
            IntentResult : A IntentResult object representing the outcome of the operation
        """
        contracts = self.query(Contract)
        result = {contract.id: contract for contract in contracts}
        return IntentResult(was_intent_successful=True, data=result)

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
