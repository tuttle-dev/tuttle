"""Test fixtures."""

import pytest
from pathlib import Path

import tuttle
from tuttle.model import Project, Client, Address, Contact, User, BankAccount


@pytest.fixture
def demo_user():
    user = User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        website="https://tuttle-dev.github.io/tuttle/",
        e_mail="mail@tuttle.com",
        phone_number="+55555555555",
        VAT_number="DZ-015",
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
def demo_projects():
    projects = []
    return projects


@pytest.fixture
def demo_clients():
    central_services = Client(
        name="Central Services",
        invoicing_contact=Contact(
            name="Central Services",
            e_mail="info@centralservices.com",
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
            e_mail="info@centralservices.com",
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
def demo_calendar_timetracking():
    timetracking_calendar_path = Path("tests/data/TuttleDemo-TimeTracking.ics")
    cal = tuttle.calendar.FileCalendar(
        path=timetracking_calendar_path, name="TimeTracking"
    )
    return cal
