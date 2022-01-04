"""Main application."""
from pathlib import Path
import os

import sqlmodel

import model

from model import Timesheet, Project, Invoice


class App:
    """The main application class"""

    def __init__(
        self,
    ):
        self.home = Path.home() / ".tuttle"
        if not os.path.exists(self.home):
            os.mkdir(self.home)
        self.db_path = self.home / "tuttle.db"
        self.db_engine = sqlmodel.create_engine(f"sqlite:///{self.db_path}", echo=True)
        sqlmodel.SQLModel.metadata.create_all(self.db_engine)

    def generate_timesheet(self, project: Project, time_period) -> Timesheet:
        """."""
        raise NotImplementedError("TODO")

    def generate_invoice(timesheet: Timesheet) -> Invoice:
        """."""
        raise NotImplementedError("TODO")
