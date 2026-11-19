"""Opening a user's database: one way to build the engine, and a session for one piece of work."""

import sqlite3
import threading

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, pool, select

import tuttle.app.core.abstractions as abstractions
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.core.user_db import create_user_db_engine, user_db_session
from tuttle.model import Address, ClientContact


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "user.db"
    engine = create_user_db_engine(path)
    SQLModel.metadata.create_all(engine)
    engine.dispose()
    return path


def _foreign_keys_on(engine) -> bool:
    with engine.connect() as connection:
        return connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def _raw_connection(session) -> sqlite3.Connection:
    return session.connection().connection.dbapi_connection


def test_engine_enforces_foreign_keys(db_path):
    engine = create_user_db_engine(db_path)

    assert _foreign_keys_on(engine)

    engine.dispose()


def test_engine_has_one_connection_that_any_thread_may_use(db_path):
    engine = create_user_db_engine(db_path)
    assert isinstance(engine.pool, pool.StaticPool)
    assert _foreign_keys_on(engine)

    seen = []
    thread = threading.Thread(target=lambda: seen.append(_foreign_keys_on(engine)))
    thread.start()
    thread.join()

    assert seen == [True]
    engine.dispose()


def test_session_reads_what_another_session_wrote(db_path):
    with user_db_session(db_path) as session:
        address = Address(street="Main Street", number="9999", city="Sao Paolo")
        session.add(address)
        session.commit()

    # Still readable after the commit and outside the session.
    assert address.city == "Sao Paolo"
    with user_db_session(db_path) as session:
        assert [a.street for a in session.exec(select(Address)).all()] == ["Main Street"]


def test_session_enforces_foreign_keys(db_path):
    with user_db_session(db_path) as session:
        session.add(ClientContact(client_id=999, contact_id=999))

        with pytest.raises(IntegrityError):
            session.commit()


def test_engine_is_disposed_after_the_block(db_path):
    with user_db_session(db_path) as session:
        connection = _raw_connection(session)
        connection.execute("SELECT 1")

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_engine_is_disposed_when_the_block_raises(db_path):
    with pytest.raises(RuntimeError, match="the work failed"):
        with user_db_session(db_path) as session:
            connection = _raw_connection(session)
            raise RuntimeError("the work failed")

    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_every_data_source_builds_its_own_engine(db_path, monkeypatch):
    """Sharing one would put them all on a single connection and in each other's transactions."""
    monkeypatch.setattr(abstractions, "_active_db_path", db_path)

    first, second = SQLModelDataSourceMixin(), SQLModelDataSourceMixin()

    assert first.db_engine is not second.db_engine
    assert str(first.db_engine.url) == f"sqlite:///{db_path}"
    assert isinstance(first.db_engine.pool, pool.StaticPool)
    assert _foreign_keys_on(first.db_engine)
