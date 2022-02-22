"""Main application."""
from pathlib import Path
import os

import sqlmodel

from . import model


class App:
    """The main application class"""

    def __init__(self, debug_mode=False, verbose=False):
        if debug_mode:
            self.home = Path("./test_home")
        else:
            self.home = Path.home() / ".tuttle"
        if not os.path.exists(self.home):
            os.mkdir(self.home)
        self.db_path = self.home / "tuttle.db"
        self.db_engine = sqlmodel.create_engine(
            f"sqlite:///{self.db_path}",
            echo=verbose,
        )
        sqlmodel.SQLModel.metadata.create_all(self.db_engine)
        self.db_session = self.get_session()

    def get_session(self):
        return sqlmodel.Session(
            self.db_engine,
            expire_on_commit=False,
        )

    def clear_database(self):
        """
        Delete the database and rebuild database model.
        """
        self.db_path.unlink()
        self.db_engine = sqlmodel.create_engine(f"sqlite:///{self.db_path}", echo=True)
        sqlmodel.SQLModel.metadata.create_all(self.db_engine)

    def store(self, entity):
        """Store an entity in the database."""
        with self.get_session() as session:
            session.add(entity)
            session.commit()

    def store_all(self, entities):
        """Store a collection of entities in the database."""
        with self.get_session() as session:
            for entity in entities:
                session.add(entity)
            session.commit()

    def retrieve_all(self, entity_type):
        with self.get_session() as session:
            entities = session.exec(
                sqlmodel.select(entity_type),
            ).all()
            return entities

    @property
    def contracts(self):
        contracts = self.db_session.exec(
            sqlmodel.select(model.Contract),
        ).all()
        return contracts

    @property
    def projects(self):
        contracts = self.db_session.exec(
            sqlmodel.select(model.Project),
        ).all()
        return contracts

    @property
    def user(self):
        user = self.db_session.exec(sqlmodel.select(model.User)).one()
        return user

    def get_project(self, title: str):
        """Get a project by its title."""
        project = self.db_session.exec(
            (sqlmodel.select(model.Project).where(model.Project.title == title))
        ).one()
        return project
