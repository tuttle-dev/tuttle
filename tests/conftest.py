"""Test fixtures."""

import pytest
from pathlib import Path
import datetime

import tuttle
from tuttle.model import Project, Client, Address, Contact, User, BankAccount, Contract


@pytest.fixture
def demo_user():
    user = User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        website="https://tuttle-dev.github.io/tuttle/",
        email="mail@tuttle.com",
        phone_number="+55555555555",
        VAT_number="27B-6",
        address=Address(
            name="Harry Tuttle",
            street="Main Street",
            number="450",
            city="Sao Paolo",
            postal_code="555555",
            country="Brazil",
        ),
        bank_account=BankAccount(
            name="Giro",
            IBAN="BZ99830994950003161565",
        ),
    )
    return user


@pytest.fixture
def demo_clients():
    central_services = Client(
        name="Central Services",
        invoicing_contact=Contact(
            name="Central Services",
            email="info@centralservices.com",
            address=Address(
                street="Main Street",
                number="42",
                postal_code="55555",
                city="Sao Paolo",
                country="Brazil",
            ),
        ),
    )

    sam_lowry = Client(
        name="Sam Lowry",
        invoicing_contact=Contact(
            name="Sam Lowry",
            email="info@centralservices.com",
            address=Address(
                street="Main Street",
                number="9999",
                postal_code="55555",
                city="Sao Paolo",
                country="Brazil",
            ),
        ),
    )

    clients = [
        central_services,
        sam_lowry,
    ]

    return clients


@pytest.fixture
def demo_contracts(demo_clients):
    heating_engineering_contract = Contract(
        title="Heating Engineering Contract",
        client=demo_clients[0],
        rate=100.00,
        currency="EUR",
        unit=tuttle.time.TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=tuttle.time.Cycle.monthly,
    )

    heating_repair_contract = Contract(
        title="Heating Repair Contract",
        client=demo_clients[1],
        rate=50.00,
        currency="EUR",
        unit=tuttle.time.TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=tuttle.time.Cycle.monthly,
    )

    contracts = [
        heating_engineering_contract,
        heating_repair_contract,
    ]
    return contracts


@pytest.fixture
def demo_projects(demo_contracts):
    heating_engineering = Project(
        title="Heating Engineering",
        tag="#HeatingEngineering",
        contract=demo_contracts[0],
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 3, 31),
    )

    heating_repair = Project(
        title="Heating Repair",
        tag="#HeatingRepair",
        contract=demo_contracts[1],
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 3, 31),
    )
    projects = [heating_engineering, heating_repair]
    return projects


@pytest.fixture
def demo_calendar_timetracking():
    timetracking_calendar_path = Path("tests/data/TuttleDemo-TimeTracking.ics")
    cal = tuttle.calendar.FileCalendar(
        path=timetracking_calendar_path, name="TimeTracking"
    )
    return cal
