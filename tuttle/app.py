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


the_app = App()
