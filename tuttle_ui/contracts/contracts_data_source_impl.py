from decimal import Decimal

from pydantic import condecimal
from typing import Mapping
from core.models import Cycle, TimeUnit
import datetime
from .abstractions import ContractDataSource
from .utils import ContractIntentsResult
from .contract_model import Contract
from clients.client_model import Client, create_client_from_title


class ContractDataSourceImpl(ContractDataSource):
    def __init__(self):
        super().__init__()
        self.contracts: Mapping[str, Contract] = {}
        self.clients: Mapping[str, Client] = {}

    def get_all_contracts_as_map(
        self,
    ) -> ContractIntentsResult:
        self._set_dummy_contracts()
        return ContractIntentsResult(wasIntentSuccessful=True, data=self.contracts)

    def get_all_clients_as_map(self):
        return self.clients

    def create_client(self, title: str) -> ContractIntentsResult:
        client = create_client_from_title(title=title)
        self.clients[str(client.id)] = client
        return ContractIntentsResult(wasIntentSuccessful=True, data=client.id)

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
        return ContractIntentsResult(wasIntentSuccessful=False)

    def get_contract_by_id(self, contractId) -> ContractIntentsResult:
        i = int(contractId)
        c = Contract(
            id=i,
            client_id=i * 3,
            title=f"Tuttle Ui Development Phase {i}",
            rate=i * 2.2,
            volume=int(i * 3.4),
            currency="usd",
            VAT_rate=i * 0.2,
            billing_cycle=Cycle.hourly,
            term_of_payment=12,
            unit=TimeUnit.hour,
            units_per_workday=i * 2.4,
            is_completed=True if i % 2 == 0 else False,
            signature_date=datetime.date.today(),
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta((i + 1)),
        )
        return c

    """DUMMY CONTENT BELOW ---  DELETE ALL"""

    def _set_dummy_contracts(self):
        self.contracts.clear()
        total = 50
        for i in range(total):
            c = Contract(
                id=i,
                client_id=i * 3,
                title=f"Tuttle Ui Development Phase {i}",
                rate=i * 2.2,
                volume=int(i * 3.4),
                currency="usd",
                VAT_rate=i * 0.2,
                billing_cycle=Cycle.hourly,
                term_of_payment=12,
                unit=TimeUnit.hour,
                units_per_workday=i * 2.4,
                is_completed=True if i % 2 == 0 else False,
                signature_date=datetime.date.today(),
                start_date=datetime.date.today(),
                end_date=datetime.date.today() + datetime.timedelta((i + 1)),
            )
            self.contracts[c.id] = c
