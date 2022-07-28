#!/usr/bin/env python

"""Tests for the database model."""

from pathlib import Path
from tracemalloc import stop
from loguru import logger
from sqlmodel import create_engine, SQLModel, Session, select
import sqlite3
import os
import datetime

from tuttle import model, time


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
        test_home = Path("tests/data/tmp")
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
        tag="#heating",
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=80),
    )
    assert store_and_retrieve(project)


def test_contract():

    the_client = model.Client(
        name="Central Services",
        invoicing_contact=model.Contact(
            name="Central Services",
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
