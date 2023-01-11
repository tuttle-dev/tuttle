from typing import Callable, Type, Optional, List
from abc import ABC, abstractmethod
from flet import AlertDialog
from loguru import logger
import sqlmodel
from pathlib import Path
from dataclasses import dataclass
from .models import IntentResult
from .utils import AlertDialogControls, START_ALIGNMENT, AUTO_SCROLL


class ClientStorage(ABC):
    """An abstraction that defines methods for caching data"""

    def __init__(
        self,
    ):
        super().__init__()
        self.keys_prefix = "tuttle_app"

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


@dataclass
class TuttleViewParams:
    navigate_to_route: Callable
    show_snack: Callable
    dialog_controller: Callable
    upload_file_callback: Callable
    pick_file_callback: Callable
    local_storage: Optional[ClientStorage] = None
    vertical_alignment_in_parent: str = START_ALIGNMENT
    horizontal_alignment_in_parent: str = START_ALIGNMENT
    keep_back_stack = True
    on_navigate_back: Optional[Callable] = None
    page_scroll_type: Optional[str] = AUTO_SCROLL


class TuttleView(ABC):
    """Abstract class for all UI screens"""

    def __init__(self, params: TuttleViewParams):
        super().__init__()
        self.navigate_to_route = params.navigate_to_route
        self.show_snack = params.show_snack
        self.dialog_controller = params.dialog_controller
        self.vertical_alignment_in_parent = params.vertical_alignment_in_parent
        self.horizontal_alignment_in_parent = params.horizontal_alignment_in_parent
        self.keep_back_stack = params.keep_back_stack
        self.on_navigate_back = params.on_navigate_back
        self.page_scroll_type = params.page_scroll_type
        self.upload_file_callback = params.upload_file_callback
        self.pick_file_callback = params.pick_file_callback
        self.mounted = False

    def parent_intent_listener(self, intent: str, data: any):
        """listens for an intent from parent view"""
        return None

    def on_window_resized(self, width, height):
        """sets the page width and height"""
        self.page_width = width
        self.page_height = height


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
        logger.info(f"Creating {self.__class__.__name__} with db_path: {db_path}")
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
