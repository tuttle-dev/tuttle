"""Tests for the database model."""

import datetime
import os
import sqlite3
from pathlib import Path
from tracemalloc import stop

import pytest
from loguru import logger
from pydantic import EmailStr, ValidationError
from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
    select,
    delete,
)
import sqlalchemy

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


@pytest.fixture
def engine():
    # in-memory sqlite db
    engine = create_engine("sqlite:///", echo=True)
    sqlalchemy.event.listen(
        engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys = ON")
    )

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    return engine


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


class TestUser:
    """Tests for the User model."""

    def test_valid_instantiation(self):
        user = User.validate(
            dict(
                name="Harry Tuttle",
                subtitle="Heating Engineer",
                email="harry@tuttle.com",
            )
        )


class TestContact:
    def test_valid_instantiation(self):
        contact = Contact.validate(
            dict(
                first_name="Sam",
                last_name="Lowry",
                email="sam.lowry@miniinf.gov",
                company="Ministry of Information",
            )
        )
        assert store_and_retrieve(contact)

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            Contact.validate(
                dict(
                    first_name="Sam",
                    last_name="Lowry",
                    email="27B-",
                    company="Ministry of Information",
                )
            )

    def test_delete_if_required(self, engine):
        """Test that a contact can be deleted if it is not required by a client."""
        contact = Contact.validate(
            dict(
                first_name="Sam",
                last_name="Lowry",
                email="sam.lowry@miniinf.gov",
                company="Ministry of Information",
            )
        )
        client = Client.validate(
            dict(
                name="Ministry of Information",
                invoicing_contact=contact,
            )
        )

        with pytest.raises(sqlalchemy.exc.IntegrityError):
            with Session(engine) as session:
                session.add(client)
                session.commit()
                session.refresh(client)

                session.exec(delete(Contact).where(Contact.id == 1))
                session.commit()


class TestClient:
    """Tests for the Client model."""

    def test_valid_instantiation(self):
        invoicing_contact = Contact(
            first_name="Sam",
            last_name="Lowry",
            email="sam.lowry@miniinf.gov",
            company="Ministry of Information",
        )
        client = Client.validate(
            dict(
                name="Ministry of Information",
                invoicing_contact=invoicing_contact,
            )
        )
        assert store_and_retrieve(client)

    def test_missing_name(self):
        """Test that a ValidationError is raised when the name is missing."""
        with pytest.raises(ValidationError):
            Client.validate(dict())

        try:
            client = Client.validate(dict())
        except ValidationError as ve:
            for error in ve.errors():
                field_name = error.get("loc")[0]
                error_message = error.get("msg")
                assert field_name == "name"

    def test_missing_fields_instantiation(self):
        with pytest.raises(ValidationError):
            Client.validate(dict())

    def test_delete_with_dependency(self, engine):
        """Test that a client can be deleted when an invoicing contact is linked."""

        contact = Contact.validate(
            dict(
                first_name="Sam",
                last_name="Lowry",
                email="sam.lowry@miniinf.gov",
                company="Ministry of Information",
            )
        )
        client = Client.validate(
            dict(
                name="Ministry of Information",
                invoicing_contact=contact,
            )
        )

        with Session(engine) as session:
            session.add(client)
            session.commit()
            session.refresh(client)

            session.exec(delete(Client).where(Client.id == 1))
            session.commit()


class TestContract:
    """Tests for the Contract model."""

    def test_valid_instantiation(self):
        client = Client(name="Ministry of Information")
        contract = Contract.validate(
            dict(
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
        )
        assert store_and_retrieve(contract)

    def test_missing_fields_instantiation(self):
        with pytest.raises(ValidationError):
            Contract.validate(dict())


class TestProject:
    """Tests for the Project model."""

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
        project = Project.validate(
            dict(
                title="Project X",
                description="The description of Project X",
                tag="#project_x",
                start_date=datetime.date(2022, 10, 2),
                end_date=datetime.date(2022, 12, 31),
                contract=contract,
            )
        )
        assert store_and_retrieve(project)

    def test_missing_fields_instantiation(self):
        with pytest.raises(ValidationError):
            Project.validate(dict())

    def test_invalid_tag_instantiation(self):
        with pytest.raises(ValidationError):
            Project.validate(
                dict(
                    title="Project X",
                    description="The description of Project X",
                    tag="project_x",
                    start_date=datetime.date(2022, 10, 2),
                    end_date=datetime.date(2022, 12, 31),
                )
            )
