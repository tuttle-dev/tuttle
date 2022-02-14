"""Main application."""
from pathlib import Path
import os

import sqlmodel

from . import model


class App:
    """The main application class"""

    def __init__(self, debug_mode=False):
        if debug_mode:
            self.home = Path("./test_home")
        else:
            self.home = Path.home() / ".tuttle"
        if not os.path.exists(self.home):
            os.mkdir(self.home)
        self.db_path = self.home / "tuttle.db"
        self.db_engine = sqlmodel.create_engine(f"sqlite:///{self.db_path}", echo=True)
        sqlmodel.SQLModel.metadata.create_all(self.db_engine)

    def get_session(self):
        return sqlmodel.Session(self.db_engine)

    def clear_database(self):
        """
        Delete the database and rebuild database model.
        """
        self.db_path.unlink()
        self.db_engine = sqlmodel.create_engine(f"sqlite:///{self.db_path}", echo=True)
        sqlmodel.SQLModel.metadata.create_all(self.db_engine)

    def get_user(self):
        with self.get_session() as session:
            user = session.exec(sqlmodel.select(model.User)).one()
        return user

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
        with self.get_session() as session:
            contracts = session.exec(
                sqlmodel.select(model.Contract),
            ).all()
            return contracts


the_app = App()
