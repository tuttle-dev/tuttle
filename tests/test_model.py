#!/usr/bin/env python

"""Tests for the database model."""

from pathlib import Path
from loguru import logger
from sqlmodel import create_engine, SQLModel, Session
import sqlite3
import os

from tuttle import model


def test_model_creation():
    """Test whether the entire data model can be materialized as DB tables."""
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

    try:
        os.remove(db_path)
    except OSError:
        pass
