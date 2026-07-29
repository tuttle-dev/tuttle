import datetime
from decimal import Decimal

import faker
import pytest

from tuttle import demo
from tuttle.model import Client, Contact, Contract, ContractCharge, Invoice, Project
from tuttle.time import ChargeBasis, TimeUnit


@pytest.fixture
def fake():
    return faker.Faker()


def test_create_fake_user(fake):
    user = demo.create_fake_user(fake)
    assert user.name is not None
    assert user.email is not None
    assert user.subtitle is not None
    assert user.VAT_number is not None


def test_create_fake_contact(fake):
    contact = demo.create_fake_contact(fake)
    assert isinstance(contact, Contact)
    assert contact.first_name is not None
    assert contact.last_name is not None
    assert contact.email is not None
    assert contact.company is not None
    assert contact.address is not None


def test_create_fake_client_with_contact(fake):
    client = demo.create_fake_client(fake, with_contact=True)
    assert isinstance(client, Client)
    assert client.name is not None
    assert client.invoicing_contact is not None


def test_create_fake_client_with_address(fake):
    client = demo.create_fake_client(fake, with_contact=False)
    assert isinstance(client, Client)
    assert client.name is not None
    assert client.invoicing_contact is None
    assert client.address is not None


def test_create_fake_contract(fake):
    contract = demo.create_fake_contract(fake)
    assert isinstance(contract, Contract)
    assert contract.title is not None
    assert contract.client is not None
    assert contract.signature_date is not None
    assert contract.start_date is not None
    assert contract.rate is not None
    assert contract.currency is not None
    assert contract.VAT_rate is not None
    assert contract.unit is not None
    assert contract.units_per_workday is not None
    assert contract.volume is not None
    assert contract.term_of_payment is not None
    assert contract.billing_cycle is not None


def test_create_fake_project(fake):
    project = demo.create_fake_project(fake)
    assert isinstance(project, Project)
    assert project.title is not None
    assert project.tag is not None
    assert project.description is not None
    assert project.is_completed is not None
    assert project.start_date is not None
    assert project.end_date is not None
    assert project.contract is not None


class TestOneTimeChargePlacement:
    """Demo invoices are built out of order, so the setup fee is placed last."""

    def _contract(self) -> Contract:
        return Contract(
            title="Retrofit",
            client=Client(name="Central Services"),
            start_date=datetime.date(2026, 1, 1),
            rate=Decimal("640"),
            currency="EUR",
            VAT_rate=Decimal("0.19"),
            unit=TimeUnit.day,
            charges=[
                ContractCharge(description="Allowance", amount=Decimal("85")),
                ContractCharge(description="Setup fee", amount=Decimal("450"), basis=ChargeBasis.once),
            ],
        )

    def _invoices(self, contract: Contract, *dates: datetime.date) -> list:
        return [Invoice(number=str(d), date=d, contract=contract) for d in dates]

    def test_lands_on_the_earliest_invoice_only(self):
        contract = self._contract()
        invoices = self._invoices(
            contract,
            datetime.date(2026, 5, 1),
            datetime.date(2026, 1, 1),
            datetime.date(2026, 3, 1),
        )

        created = demo.apply_one_time_charges(invoices)

        assert [i.description for i in created] == ["Setup fee"]
        billed = [inv for inv in invoices if any(it.contract_charge is not None for it in inv.items)]
        assert [inv.date for inv in billed] == [datetime.date(2026, 1, 1)]

    def test_contracts_without_one_time_charges_are_untouched(self):
        contract = self._contract()
        contract.charges = [ContractCharge(description="Allowance", amount=Decimal("85"))]

        assert demo.apply_one_time_charges(self._invoices(contract, datetime.date(2026, 1, 1))) == []
