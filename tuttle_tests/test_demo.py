import faker
import pytest

from tuttle.model import Contact, Client, Contract, Project, User
from tuttle import demo


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


def test_create_fake_client(fake):
    client = demo.create_fake_client(fake)
    assert isinstance(client, Client)
    assert client.name is not None
    assert client.invoicing_contact is not None


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
