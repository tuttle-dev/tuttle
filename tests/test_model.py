#!/usr/bin/env python

"""Tests for the database model."""

from pathlib import Path
from loguru import logger
from sqlmodel import create_engine, SQLModel, Session
import sqlite3
import os
import datetime

from tuttle import model


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
        subtitle="Shoe Repair Operative",
        e_mail="archibald.tuttle@centralservices.com",
    )

    icloud_account = model.ICloudAccount(
        user_name=user.e_mail,
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
    assert project.tag == "#heating"
