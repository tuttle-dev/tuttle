"""How a user's database is opened.

Each user has their own SQLite file. This is the one place that knows how an
engine on such a file is built. (``app.db``, the registry of users, is opened
by ``tuttle.app_db``.)
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import sqlalchemy
import sqlmodel
from sqlmodel import pool


def create_user_db_engine(db_path: Path | str) -> sqlalchemy.Engine:
    """Build an engine on the user database at ``db_path``, with foreign keys enforced.

    The engine holds a single connection (``StaticPool``) that any thread may
    use. Engines are not shared: every data source builds its own, so each
    works on its own connection and in its own transactions.
    """
    engine = sqlmodel.create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=pool.StaticPool,
    )
    sqlalchemy.event.listen(
        engine,
        "connect",
        lambda dbapi_conn, _: dbapi_conn.execute("PRAGMA foreign_keys = ON"),
    )
    return engine


@contextmanager
def user_db_session(db_path: Path | str) -> Iterator[sqlmodel.Session]:
    """Open the user database at ``db_path`` for one piece of work.

    For code that is not a data source and reaches into a database briefly,
    such as that of a user who is not the active one. The engine is built for
    this one session and disposed when the block ends, also when it raises.
    """
    engine = create_user_db_engine(db_path)
    try:
        with sqlmodel.Session(engine, expire_on_commit=False) as session:
            yield session
    finally:
        engine.dispose()
