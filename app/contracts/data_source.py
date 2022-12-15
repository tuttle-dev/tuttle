import datetime

from typing import Optional
from pydantic import condecimal
from decimal import Decimal
from core.models import Cycle, TimeUnit

import faker
from clients.model import Client
from core.models import IntentResult

from .model import Contract


class ContractDataSource:
    def __init__(self):
        super().__init__()
        self.contracts = {}

    def get_all_contracts_as_map(self) -> IntentResult:
        self._set_dummy_contracts()
        return IntentResult(was_intent_successful=True, data=self.contracts)

    def get_contract_by_id(self, contractId: str) -> IntentResult:
        c = self._get_fake_contract(int(contractId))
        return IntentResult(was_intent_successful=True, data=c)

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
        return IntentResult(was_intent_successful=True, data=None)

    """DUMMY CONTENT BELOW ---  DELETE ALL"""

    def _set_dummy_contracts(self):
        self.contracts.clear()
        total = 12
        for i in range(total):
            c = self._get_fake_contract(i)
            self.contracts[c.id] = c

    def _get_fake_contract(self, i):
        c = Contract(
            id=i,
            client_id=i * 3,
            client=self._get_fake_client(i * 3),
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

    def _get_fake_client(self, id):
        fake = faker.Faker(
            ["fr_FR", "en_US", "de_DE", "es_ES", "it_IT", "sv_SE", "zh_CN"]
        )
        return Client(id=id, title=fake.company(), invoicing_contact_id=int(id * 3.142))
