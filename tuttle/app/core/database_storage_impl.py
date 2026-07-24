from pathlib import Path
from typing import Callable

import sqlmodel
from loguru import logger

from ... import demo
from ...data_dir import get_data_dir
from ...db_schema import ensure_schema
from .abstractions import DatabaseStorage


class DatabaseStorageImpl(DatabaseStorage):
    """Database storage implementation."""

    def __init__(self, store_demo_timetracking_dataframe: Callable, debug_mode: bool):
        # database config
        super().__init__()
        self.app_dir = self.ensure_app_dir()
        self.db_path = self.app_dir / "tuttle.db"
        self.store_demo_dataframe_callback = store_demo_timetracking_dataframe
        self.debug_mode = debug_mode

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    def create_model(self):
        logger.info("Creating database schema")
        ensure_schema(self.db_url)

    def ensure_database(self):
        if not self.db_path.exists():
            self.db_engine = sqlmodel.create_engine(self.db_url, echo=True)
            self.create_model()
        else:
            logger.info("Database exists, ensuring schema is up to date")
            ensure_schema(self.db_url)

    def reset_database(self):
        logger.info("Clearing database")
        try:
            self.db_path.unlink()
        except FileNotFoundError:
            logger.info("Database file not found, skipping delete")
        self.db_engine = sqlmodel.create_engine(
            self.db_url,
            echo=self.debug_mode,
        )
        self.create_model()

    def install_demo_data(
        self,
    ):
        self.reset_database()
        try:
            demo.install_demo_data(
                n_projects=4,
                db_path=self.db_path,
                on_cache_timetracking_dataframe=self.store_demo_dataframe_callback,
            )
            logger.info("Demo data installation completed")
        except Exception as ex:
            logger.exception(ex)
            logger.error("Failed to install demo data")

    def ensure_app_dir(self) -> Path:
        app_dir = get_data_dir()
        if not app_dir.exists():
            app_dir.mkdir(parents=True)
        return app_dir
