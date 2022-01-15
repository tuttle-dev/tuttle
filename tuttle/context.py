from pathlib import Path
import os
import sqlmodel

from . import model


class Context:
    def __init__(self):
        self.tuttle_home = Path.home() / ".tuttle"
        if not os.path.exists(self.tuttle_home):
            os.mkdir(self.tuttle_home)
        self.db_path = self.tuttle_home / "tuttle.db"
        self.db_engine = sqlmodel.create_engine(f"sqlite:///{self.db_path}", echo=True)
        sqlmodel.SQLModel.metadata.create_all(self.db_engine)


def get_context() -> Context:
    return Context()
