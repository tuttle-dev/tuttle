from datetime import date

import faker
import pytest

from tuttle import demo
from tuttle.calendar import ICSCalendar
from tuttle.model import Client, Contact, Contract, Project
from tuttle.time import ChargeBasis


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


class TestHarryTuttle:
    """The demo user shows every feature, on whatever day the demo is installed."""

    # A weekday, the turn of the year, a Sunday, and New Year's Eve.
    @pytest.fixture(params=[date(2026, 10, 23), date(2026, 1, 2), date(2026, 3, 1), date(2026, 12, 31)], ids=str)
    def today(self, request) -> date:
        return request.param

    @pytest.fixture
    def demo_data(self, today):
        projects, _ = demo.create_demo_business(demo.create_demo_user(), today)
        calendar = ICSCalendar(name="Demo calendar", ics_calendar=demo.create_fake_calendar(list(projects.values()), today))
        return projects, demo.create_demo_invoices(projects, calendar.to_data(), today)

    def test_every_stage_of_the_project_board_has_a_project(self, demo_data, today):
        projects, _ = demo_data
        assert {p.board_stage(today) for p in projects.values()} == {"Lead", "Offer", "Upcoming", "Active", "Completed"}

    def test_every_kind_of_invoice_is_there(self, demo_data, today):
        _, invoices = demo_data
        assert {i.document_type for i in invoices} == {"invoice", "reminder", "deposit", "final"}
        assert any(i.cancelled for i in invoices)
        assert any(not i.sent for i in invoices), "a draft"
        assert any(i.reminders for i in invoices), "an invoice with a payment reminder"
        assert any(i.sent and not i.paid and i.due_date < today and not i.reminders and not i.is_reminder for i in invoices), (
            "an overdue invoice waiting for its reminder"
        )
        assert any(i.currency == "USD" for i in invoices)
        assert all(i.date <= today for i in invoices)

    def test_tracked_time_is_billed_once(self, demo_data):
        _, invoices = demo_data
        billed = set()
        for invoice in invoices:
            if invoice.cancelled:
                continue
            for timesheet in invoice.timesheets:
                for item in timesheet.items:
                    assert (item.tag, item.begin) not in billed
                    billed.add((item.tag, item.begin))
        assert billed

    def test_the_one_time_charge_is_billed_once(self, demo_data):
        _, invoices = demo_data
        one_time = [
            item
            for invoice in invoices
            if not invoice.cancelled
            for item in invoice.items
            if item.contract_charge is not None and item.contract_charge.basis == ChargeBasis.once
        ]
        assert len(one_time) == 1
