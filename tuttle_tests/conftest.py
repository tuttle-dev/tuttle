"""Test fixtures."""

import pytest
from pathlib import Path
import datetime
from decimal import Decimal

import tuttle
from tuttle import fx
from tuttle.model import Project, Client, Address, Contact, User, BankAccount, Contract

# Every non-EUR amount in the suite converts at this rate. A fixed number keeps
# assertions stable; the real ECB average would make them depend on the day.
STUB_FX_RATE = Decimal("0.9")


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Keep tests out of the real ~/.tuttle — they must not read the
    developer's settings or write fx rate caches into production app.db."""
    monkeypatch.setenv("TUTTLE_DATA_DIR", str(tmp_path / "tuttle-data"))


@pytest.fixture(autouse=True)
def offline_fx(monkeypatch):
    """Cut the two paths in ``fx`` that reach the network.

    The suite must not depend on frankfurter.dev being up, and a rate cached
    against one test's app.db must not leak into the next, so the caches are
    cleared before each test — while the real functions are still in place.
    """
    fx.clear_cache()
    monkeypatch.setattr(fx, "supported_currencies", lambda: fx.SUPPORTED_CURRENCIES)
    monkeypatch.setattr(
        fx,
        "_fetch_monthly_average",
        lambda base, quote, month: STUB_FX_RATE,
    )


@pytest.fixture
def demo_contact():
    return Contact(
        fist_name="Sam",
        last_name="Lowry",
        email="info@centralservices.com",
        address=Address(
            street="Main Street",
            number="9999",
            postal_code="55555",
            city="Sao Paolo",
            country="Brazil",
        ),
    )


@pytest.fixture
def demo_user():
    user = User(
        first_name="Harry",
        last_name="Tuttle",
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
            BIC="BANKINFO101",
        ),
    )
    return user


@pytest.fixture
def demo_clients():
    central_services = Client(
        name="Central Services",
        address=Address(
            street="Main Street",
            number="42",
            postal_code="55555",
            city="Sao Paolo",
            country="Brazil",
        ),
    )

    sam_lowry = Client(
        name="Sam Lowry",
        invoicing_contact=Contact(
            first_name="Sam",
            last_name="Lowry",
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
        rate=0,
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
    timetracking_calendar_path = Path("tuttle_tests/data/TuttleDemo-TimeTracking.ics")
    cal = tuttle.calendar.ICSCalendar(
        path=timetracking_calendar_path, name="TimeTracking"
    )
    return cal
