from typing import Any, Callable, List, Optional, Type

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import functools

from flet import AlertDialog, file_picker

import sqlmodel
from core.intent_result import IntentResult
from loguru import logger

from .utils import AUTO_SCROLL, START_ALIGNMENT, AlertDialogControls


class ClientStorage(ABC):
    """Abstract class for client storage"""

    def __init__(
        self,
    ):
        super().__init__()
        self.keys_prefix = "tuttle_app_"

    @abstractmethod
    def set_value(self, key: str, value: any):
        """appends an identifier prefix to the key and stores the key-value pair
        value can be a string, number, boolean or list
        """
        pass

    @abstractmethod
    def get_value(self, key: str) -> Optional[any]:
        """appends an identifier prefix to the key and gets the value if exists"""
        pass

    @abstractmethod
    def remove_value(self, key: str):
        """appends an identifier prefix to the key and removes associated key-value pair if exists"""
        pass

    @abstractmethod
    def clear_preferences(
        self,
    ):
        """Deletes all of preferences permanently"""
        pass


@dataclass
class TuttleViewParams:
    navigate_to_route: Callable
    show_snack: Callable
    dialog_controller: Callable
    upload_file_callback: Callable
    pick_file_callback: Callable[[file_picker.FilePickerFile], str]
    client_storage: Optional[ClientStorage] = None
    vertical_alignment_in_parent: str = START_ALIGNMENT
    horizontal_alignment_in_parent: str = START_ALIGNMENT
    keep_back_stack: bool = True
    on_navigate_back: Optional[Callable] = None
    page_scroll_type: Optional[str] = AUTO_SCROLL


class TuttleView(ABC):
    """Abstract class for all UI screens"""

    def __init__(self, params: TuttleViewParams):
        super().__init__()
        self.navigate_to_route = params.navigate_to_route
        self.show_snack: Callable[[str, bool], None] = params.show_snack
        self.dialog_controller = params.dialog_controller
        self.vertical_alignment_in_parent = params.vertical_alignment_in_parent
        self.horizontal_alignment_in_parent = params.horizontal_alignment_in_parent
        self.keep_back_stack = params.keep_back_stack
        self.on_navigate_back = params.on_navigate_back
        self.page_scroll_type = params.page_scroll_type
        self.upload_file_callback = params.upload_file_callback
        self.pick_file_callback = params.pick_file_callback
        self.client_storage = params.client_storage
        self.mounted = False

    def parent_intent_listener(self, intent: str, data: any):
        """listens for an intent from parent view"""
        return

    def on_resume_after_back_pressed(
        self,
    ):
        """listener for when a view has been resumed after user pressed back from another view
        used by views whose self.keep_back_stack parameter is set to True
        """
        return

    def on_window_resized_listener(self, width, height):
        """sets the page width and height"""
        self.page_width = width
        self.page_height = height

    def update_self(
        self,
    ):
        """Triggers an update to the view only if the view is mounted"""
        try:
            if self.mounted:
                self.update()
        except Exception as e:
            logger.error(
                f"A view update caused an exception to be thrown {e.__class__.__name__}"
            )
            logger.exception(e)


class DialogHandler(ABC):
    """Used by views to set, open, and dismiss dialogs"""

    def __init__(
        self,
        dialog: AlertDialog,
        dialog_controller: Callable[[any, AlertDialogControls], None],
    ):
        super().__init__()
        self.dialog_controller = dialog_controller
        self.dialog: AlertDialog = dialog

    def close_dialog(self, e: Optional[any] = None):
        self.dialog_controller(self.dialog, AlertDialogControls.CLOSE)

    def open_dialog(self, e: Optional[any] = None):
        self.dialog_controller(self.dialog, AlertDialogControls.ADD_AND_OPEN)

    def dimiss_open_dialogs(self):
        if self.dialog is not None and self.dialog.open:
            self.close_dialog()


class SQLModelDataSourceMixin:
    """Implements common methods for data sources that interact with SQLModel"""

    def __init__(
        self,
    ):
        db_path = Path.home() / ".tuttle" / "tuttle.db"
        db_path = f"sqlite:///{db_path}"
        logger.debug(f"Creating {self.__class__.__name__} with db_path: {db_path}")
        self.db_engine = sqlmodel.create_engine(
            db_path,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=sqlmodel.pool.StaticPool,
        )

    def create_session(self):
        return sqlmodel.Session(
            self.db_engine,
            expire_on_commit=False,
        )

    def query(self, entity_type: Type[sqlmodel.SQLModel]) -> List:
        """Queries the database for all instances of the given entity type"""
        logger.debug(f"querying {entity_type}")
        with self.create_session() as session:
            entities = session.exec(sqlmodel.select(entity_type)).all()
        if len(entities) == 0:
            logger.warning(f"No instances of {entity_type} found")
        else:
            logger.debug(f"Found {len(entities)} instances of {entity_type}")
        return entities

    def query_by_id(
        self,
        entity_type: Type[sqlmodel.SQLModel],
        entity_id: int,
    ) -> Optional[sqlmodel.SQLModel]:
        """Queries the database for an instance of the given entity type with the given id"""
        logger.debug(f"querying {entity_type} by id={entity_id}")
        with self.create_session() as session:
            entity = session.exec(
                sqlmodel.select(entity_type).where(entity_type.id == entity_id)
            ).one()
        if entity is None:
            logger.warning(f"No instance of {entity_type} found with id={entity_id}")
        else:
            logger.info(f"Found instance of {entity_type} with id={entity_id}")
        return entity

    def query_where(
        self,
        entity_type: Type[sqlmodel.SQLModel],
        field_name: str,
        field_value: Any,
    ) -> List:
        """Queries the database for all instances of the given entity type that have the given field value"""
        logger.debug(f"querying {entity_type} by {field_name}={field_value}")
        with self.create_session() as session:
            entities = session.exec(
                sqlmodel.select(entity_type).where(
                    getattr(entity_type, field_name) == field_value
                )
            ).all()
        if len(entities) == 0:
            logger.warning(f"No instances of {entity_type} found")
        else:
            logger.info(f"Found {len(entities)} instances of {entity_type}")
        return entities

    def query_the_only(self, entity_type: Type[sqlmodel.SQLModel]) -> sqlmodel.SQLModel:
        """Queries the database for the only instance of the given entity type. Raises an error if there are more than one"""
        entities = self.query(entity_type)
        if len(entities) > 1:
            raise Exception(f"More than one {entity_type} found")
        elif len(entities) == 1:
            return entities[0]
        else:
            return None

    def store(self, entity: sqlmodel.SQLModel):
        """Stores the given entity in the database"""
        logger.debug(f"storing {entity}")
        with self.create_session() as session:
            session.add(entity)
            session.commit()
            session.refresh(entity)

    def delete_by_id(self, entity_type: Type[sqlmodel.SQLModel], entity_id: int):
        """Deletes the entity of the given type with the given id from the database"""
        logger.debug(f"deleting {entity_type} with id={entity_id}")
        with self.create_session() as session:
            session.exec(
                sqlmodel.delete(entity_type).where(entity_type.id == entity_id)
            )
            session.commit()


class Intent(ABC):
    """Abstract base class for intent classes."""

    def __getattribute__(self, name):
        """Logs all calls to methods of this class""" ""
        attr = object.__getattribute__(self, name)
        if callable(attr):

            @functools.wraps(attr)
            def wrapped(*args, **kwargs):
                class_name = self.__class__.__name__
                # Mask password argument if exists
                kwargs = {
                    k: "******" if k == "password" else v for k, v in kwargs.items()
                }
                logger.debug(f"Intent: {class_name}:{name} called with: {kwargs}")
                return attr(*args, **kwargs)

            return wrapped
        return attr
