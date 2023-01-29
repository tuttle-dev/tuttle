"""Tests for the database model."""

import datetime
import os
import sqlite3
from pathlib import Path
from tracemalloc import stop

import pytest
from loguru import logger
from pydantic import EmailStr, ValidationError
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle import model, time
from tuttle.model import (
    Address,
    Client,
    Contact,
    Contract,
    Project,
    User,
    TimeUnit,
    Cycle,
)


def store_and_retrieve(model_object):
    # in-memory sqlite db
    db_engine = create_engine("sqlite:///")
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        session.add(model_object)
        session.commit()
    with Session(db_engine) as session:
        retrieved = session.exec((select(type(model_object)))).first()
    return True


def test_model_creation():
    """Test whether the entire data model can be materialized as DB tables."""
    try:
        test_home = Path("tuttle_tests/data/tmp")
        db_path = test_home / "tuttle_test.db"
        db_url = f"sqlite:///{db_path}"
        db_engine = create_engine(db_url, echo=True)
        SQLModel.metadata.create_all(db_engine)

        # test if database intact
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name;
            """
        )
        tables = cursor.fetchall()
        conn.close()
    finally:
        try:
            os.remove(db_path)
        except OSError:
            pass


def test_user():
    user = model.User(
        name="Archibald Tuttle",
        subtitle="Heating Engineer",
        email="harry@tuttle.com",
    )

    icloud_account = model.ICloudAccount(
        user_name=user.email,
    )

    user.icloud_account = icloud_account

    assert icloud_account.user.name == "Archibald Tuttle"


def test_project():
    project = model.Project(
        title="Heating Repair",
        tag="#heating-repair",
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=80),
    )
    assert store_and_retrieve(project)


def test_contract():

    the_client = model.Client(
        name="Central Services",
        invoicing_contact=model.Contact(
            first_name="Central",
            last_name="Services",
            company="Central Services",
            address=model.Address(
                street="Down the Road",
                number="55",
                city="Somewhere",
                postal_code="99999",
                country="Brazil",
            ),
            email="mail@centralservices.com",
        ),
    )

    the_contract = model.Contract(
        title="CS Q1 2022",
        client=the_client,
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 3, 31),
        signature_date=datetime.date(2021, 10, 31),
        rate=100,
        unit=time.TimeUnit.hour,
        currency="EUR",
        billing_cycle=time.Cycle.monthly,
        volume=3 * 8 * 8,
        units_per_workday=8,
    )
    assert store_and_retrieve(the_contract)


class TestContact:
    def test_valid_contact_instantiation(self):
        contact = Contact(
            first_name="Sam",
            last_name="Lowry",
            email="sam.lowry@miniinf.gov",
            company="Ministry of Information",
        )
        assert store_and_retrieve(contact)

    def test_invalid_email_instantiation(self):
        with pytest.raises(ValidationError):
            Contact.validate(
                dict(
                    first_name="Sam",
                    last_name="Lowry",
                    email="27B-",
                    company="Ministry of Information",
                )
            )


class TestClient:
    def test_valid_instantiation(self):
        invoicing_contact = Contact(
            first_name="Sam",
            last_name="Lowry",
            email="sam.lowry@miniinf.gov",
            company="Ministry of Information",
        )
        client = Client(
            name="Ministry of Information", invoicing_contact=invoicing_contact
        )
        assert store_and_retrieve(client)

    def test_missing_fields_instantiation(self):
        with pytest.raises(ValidationError):
            Client()  # type: ignore


class TestContract:
    def test_valid_instantiation(self):
        client = Client(name="Ministry of Information")
        contract = Contract(
            title="Project X Contract",
            client=client,
            signature_date=datetime.date(2022, 10, 1),
            start_date=datetime.date(2022, 10, 2),
            end_date=datetime.date(2022, 12, 31),
            rate=100,
            is_completed=False,
            currency="USD",
            VAT_rate=0.19,
            unit=TimeUnit.hour,
            units_per_workday=8,
            volume=100,
            term_of_payment=31,
            billing_cycle=Cycle.monthly,
        )
        assert store_and_retrieve(contract)

    def test_missing_fields_instantiation(self):
        with pytest.raises(ValidationError):
            Contract()  # type: ignore
