from __future__ import annotations

import datetime
import functools
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Mapping, Optional, Type

import sqlalchemy
import sqlmodel
from loguru import logger
from pydantic import ValidationError
from sqlmodel import pool

from ...data_dir import get_data_dir
from .intent_result import IntentResult


def _coerce_dates(data: dict) -> dict:
    """Convert ISO date strings to ``datetime.date`` for ``*_date`` keys."""
    for k in list(data):
        if k.endswith("_date"):
            v = data[k]
            if v == "" or v is None:
                data[k] = None
            elif isinstance(v, str) and len(v) >= 10:
                try:
                    data[k] = datetime.date.fromisoformat(v[:10])
                except ValueError:
                    pass
    return data


def _validation_error_message(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        field = loc[0] if loc else "field"
        msg = err.get("msg", "invalid value")
        if msg.startswith("Value error, "):
            msg = msg.removeprefix("Value error, ")
        parts.append(f"{field}: {msg}")
    return "; ".join(parts) or "Validation failed."


class DatabaseStorage(ABC):
    """Abstract class for database storage"""

    def __init__(
        self,
    ):
        super().__init__()

    @abstractmethod
    def create_model(self):
        """Creates database model"""
        pass

    @abstractmethod
    def ensure_database(self):
        """
        Ensure that the database exists and is up to date.
        """
        pass

    @abstractmethod
    def reset_database(self):
        """
        Delete the database and rebuild database model.
        """
        pass

    @abstractmethod
    def install_demo_data(
        self,
    ):
        """Install demo data into the database."""

    @abstractmethod
    def ensure_app_dir(self) -> Path:
        """Ensures that the user directory exists"""
        pass


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


# ---------------------------------------------------------------------------
# Active per-user database path (module-level state)
# ---------------------------------------------------------------------------

_active_db_path: Path = get_data_dir() / "tuttle.db"


def set_active_db(path: Path) -> None:
    """Switch all new data-source instances to use *path* as their SQLite DB."""
    global _active_db_path
    _active_db_path = path
    logger.info(f"Active user DB set to: {path}")


def get_active_db() -> Path:
    """Return the path to the currently active per-user database."""
    return _active_db_path


class SQLModelDataSourceMixin:
    """Implements common methods for data sources that interact with SQLModel"""

    def __init__(
        self,
    ):
        db_path = f"sqlite:///{_active_db_path}"
        logger.debug(f"Creating {self.__class__.__name__} with db_path: {db_path}")
        self.db_engine = sqlmodel.create_engine(
            db_path,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=pool.StaticPool,
        )
        sqlalchemy.event.listen(
            self.db_engine,
            "connect",
            lambda dbapi_conn, _: dbapi_conn.execute("PRAGMA foreign_keys = ON"),
        )

    def create_session(self):
        return sqlmodel.Session(
            self.db_engine,
            expire_on_commit=False,
        )

    def query(self, entity_type: Type[sqlmodel.SQLModel]) -> List:
        """Queries the database for all instances of the given entity type."""
        logger.debug(f"querying {entity_type}")
        with self.create_session() as session:
            entities = session.exec(sqlmodel.select(entity_type)).all()
            self._hydrate(entities)
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
        """Queries the database for an instance of the given entity type with the given id."""
        logger.debug(f"querying {entity_type} by id={entity_id}")
        with self.create_session() as session:
            entity = session.exec(sqlmodel.select(entity_type).where(entity_type.id == entity_id)).one()
            self._hydrate([entity])
        if entity is None:
            logger.warning(f"No instance of {entity_type} found with id={entity_id}")
        else:
            logger.info(f"Found instance of {entity_type} with id={entity_id}")
        return entity

    @staticmethod
    def _hydrate(entities, _depth: int = 2):
        """Touch relationship attributes while the session is still open.

        This forces SQLAlchemy to load them (via whatever lazy strategy the
        model declares) so that ``to_rpc_dict()`` can access them after the
        session closes.
        """
        if _depth <= 0 or not entities:
            return
        sample = entities[0]
        rels = getattr(sample, "__rpc_relationships__", None)
        if not rels:
            return
        names = list(rels.keys()) if isinstance(rels, dict) else list(rels)
        projections = rels if isinstance(rels, dict) else {n: None for n in names}
        for entity in entities:
            for name in names:
                value = getattr(entity, name, None)
                if value is None or projections[name] is not None:
                    continue
                children = value if isinstance(value, list) else [value]
                SQLModelDataSourceMixin._hydrate(children, _depth - 1)

    def query_where(
        self,
        entity_type: Type[sqlmodel.SQLModel],
        field_name: str,
        field_value: Any,
    ) -> List:
        """Queries the database for all instances of the given entity type that have the given field value"""
        logger.debug(f"querying {entity_type} by {field_name}={field_value}")
        with self.create_session() as session:
            entities = session.exec(sqlmodel.select(entity_type).where(getattr(entity_type, field_name) == field_value)).all()
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
        # logger.debug(f"storing {entity}")
        with self.create_session() as session:
            # Use merge instead of add so that any relationship attributes
            # pointing to detached instances (from prior sessions) are
            # re-attached in the current session, avoiding DetachedInstanceError.
            merged = session.merge(entity)
            session.commit()
            session.refresh(merged)
            # Copy DB-generated values (e.g. auto-incremented id) back to the
            # original entity so callers see the updated state.
            if getattr(entity, "id", None) is None and getattr(merged, "id", None):
                entity.id = merged.id

    def delete_by_id(self, entity_type: Type[sqlmodel.SQLModel], entity_id: int):
        """Deletes the entity of the given type with the given id from the database.

        Uses ORM-level delete so that cascade relationships are honoured.
        Raises ``sqlalchemy.exc.IntegrityError`` when a foreign-key
        constraint prevents the deletion (e.g. entity is still referenced).
        """
        logger.debug(f"deleting {entity_type} with id={entity_id}")
        with self.create_session() as session:
            entity = session.get(entity_type, entity_id)
            if entity is None:
                raise ValueError(f"{entity_type.__name__} with id={entity_id} not found")
            session.delete(entity)
            session.commit()


class Intent(ABC):
    """Abstract base class for intent classes."""

    def __getattribute__(self, name):
        """Logs all calls to methods of this class""" ""
        attr = object.__getattribute__(self, name)
        if callable(attr) and not isinstance(attr, type):

            @functools.wraps(attr)
            def wrapped(*args, **kwargs):
                class_name = self.__class__.__name__
                # Mask password argument if exists
                kwargs = {k: "******" if k == "password" else v for k, v in kwargs.items()}
                logger.debug(f"Intent: {class_name}:{name} called with: {kwargs}")
                return attr(*args, **kwargs)

            return wrapped
        return attr


class CrudIntent(SQLModelDataSourceMixin, Intent):
    """Generic CRUD intent that combines data access and business logic.

    Subclasses must set ``entity_type`` to the SQLModel class they manage.

    Declarative hooks for ``save_from_dict``::

        __save_nested__  = {"address": Address}   # nested relationship objects
        __save_skip__    = {"some_backref"}        # extra fields to ignore

    Override ``_validated_save`` to add validation before the final save.

    ``deletion_guards`` is a list of ``(relationship_attr, label, display_func)``
    tuples that produce user-friendly messages when related records still
    reference this entity.
    """

    entity_type: Type[sqlmodel.SQLModel]
    entity_name: str = ""
    deletion_guards: List[tuple] = []
    __save_nested__: dict = {}
    __save_skip__: set = set()

    def __init__(self):
        SQLModelDataSourceMixin.__init__(self)
        if not self.entity_name:
            self.entity_name = self.entity_type.__name__

    # -- Generic CRUD ----------------------------------------------------------

    def get_all(self) -> IntentResult:
        """Fetch all entities of this type."""
        try:
            entities = self.query(self.entity_type)
            return IntentResult(was_intent_successful=True, data=entities)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load {self.entity_name}s.",
                log_message=f"{self.__class__.__name__}.get_all: {e}",
                exception=e,
            )

    def get_all_as_map(self) -> Mapping[int, Any]:
        """Fetch all entities as {id: entity} dict."""
        result = self.get_all()
        if result.was_intent_successful:
            return {entity.id: entity for entity in result.data}
        result.log_message_if_any()
        return {}

    def get_by_id(self, entity_id) -> IntentResult:
        """Fetch a single entity by its id."""
        try:
            entity = self.query_by_id(self.entity_type, entity_id)
            return IntentResult(was_intent_successful=True, data=entity)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load {self.entity_name}.",
                log_message=f"{self.__class__.__name__}.get_by_id({entity_id}): {e}",
                exception=e,
            )

    def save(self, entity) -> IntentResult:
        """Create or update an entity."""
        try:
            self.store(entity)
            return IntentResult(was_intent_successful=True, data=entity)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to save {self.entity_name}.",
                log_message=f"{self.__class__.__name__}.save: {e}",
                exception=e,
            )

    def delete(self, entity_id) -> IntentResult:
        """Delete an entity by its id.

        Checks ``deletion_guards`` first to produce a user-friendly message
        when related records still reference this entity.  Falls back to the
        database-level ``IntegrityError`` as a safety net.
        """
        if self.deletion_guards:
            result = self.get_by_id(entity_id)
            if not result.was_intent_successful:
                return result
            entity = result.data
            for attr, label, display_fn in self.deletion_guards:
                related = getattr(entity, attr, None) or []
                if related:
                    names = ", ".join(display_fn(r) for r in related)
                    entity_desc = getattr(entity, "name", None) or getattr(entity, "title", f"#{entity_id}")
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg=(
                            f"Cannot delete {self.entity_name} '{entity_desc}' because it is referenced by {label}: {names}"
                        ),
                    )
        try:
            self.delete_by_id(self.entity_type, entity_id)
            return IntentResult(was_intent_successful=True)
        except sqlalchemy.exc.IntegrityError as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=(f"Cannot delete this {self.entity_name} because it is still referenced by other records."),
                log_message=f"{self.__class__.__name__}.delete({entity_id}): {e}",
                exception=e,
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to delete {self.entity_name}.",
                log_message=f"{self.__class__.__name__}.delete({entity_id}): {e}",
                exception=e,
            )

    # -- Filtered views (require is_completed / is_active / is_upcoming) -------

    def get_completed_as_map(self) -> Mapping[int, Any]:
        return {k: v for k, v in self.get_all_as_map().items() if v.is_completed}

    def get_active_as_map(self) -> Mapping[int, Any]:
        return {k: v for k, v in self.get_all_as_map().items() if v.is_active()}

    def get_upcoming_as_map(self) -> Mapping[int, Any]:
        return {k: v for k, v in self.get_all_as_map().items() if v.is_upcoming()}

    # -- Toggle helpers --------------------------------------------------------

    def toggle_completed(self, entity=None, *, id=None) -> IntentResult:
        """Toggle is_completed and save. Accepts entity or id."""
        if entity is None:
            if id is None:
                return IntentResult(was_intent_successful=False, error_msg="No entity or id provided")
            result = self.get_by_id(id)
            if not result.was_intent_successful or not result.data:
                return result
            entity = result.data
        entity.is_completed = not entity.is_completed
        result = self.save(entity)
        if not result.was_intent_successful:
            entity.is_completed = not entity.is_completed
        result.data = entity
        return result

    # -- Generic dict → entity save --------------------------------------------

    def save_from_dict(self, data: dict) -> IntentResult:
        """Create or update an entity from a plain dict.

        Handles date coercion, FK references (``{rel: {id: N}}``),
        nested relationships declared in ``__save_nested__``, and
        create-vs-update branching.  Calls ``_validated_save`` at the end.
        """
        data = _coerce_dates(dict(data))
        entity_id = data.pop("id", None)

        # Resolve FK references: {"rel": {"id": N}} → rel_id = N
        for k, v in list(data.items()):
            if isinstance(v, dict) and set(v.keys()) == {"id"}:
                fk = f"{k}_id"
                if hasattr(self.entity_type, fk):
                    data[fk] = v["id"]
                    del data[k]

        # Extract declared nested relationship data.
        # A missing key → no change.  An explicit None → clear the relationship.
        _SENTINEL = object()
        nested_raw: dict[str, dict | None] = {}
        for field in self.__save_nested__:
            val = data.pop(field, _SENTINEL)
            if val is not _SENTINEL:
                nested_raw[field] = val or None  # treat {} / falsy as None
            data.pop(f"{field}_id", None)

        skip = self.__save_skip__ | set(self.__save_nested__)
        clean = {k: v for k, v in data.items() if not k.startswith("_") and k not in skip}

        if entity_id:
            result = self.get_by_id(entity_id)
            if not result.was_intent_successful or not result.data:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg=f"{self.entity_name} not found",
                )
            entity = result.data
            for k, v in clean.items():
                setattr(entity, k, v)
            self._apply_nested(entity, nested_raw)
        else:
            children = self._build_nested(nested_raw)
            try:
                entity = self.entity_type.model_validate({**clean, **children})
            except ValidationError as exc:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg=_validation_error_message(exc),
                    exception=exc,
                )

        try:
            self.entity_type.model_validate(entity.model_dump())
        except ValidationError as exc:
            return IntentResult(
                was_intent_successful=False,
                error_msg=_validation_error_message(exc),
                exception=exc,
            )

        return self._validated_save(entity)

    def get_field_requirements(self) -> IntentResult:
        """Return field metadata derived from the model schema.

        The model class is the single source of truth for which fields are
        required.  This RPC endpoint exposes that information to the frontend
        so forms can render indicators without manual duplication.
        """
        fields = {}
        for name, field_info in self.entity_type.model_fields.items():
            if name == "id" or name.endswith("_id"):
                continue
            annotation = field_info.annotation
            origin = getattr(annotation, "__origin__", None)
            if origin is list:
                continue
            label = field_info.description or name.replace("_", " ").title()
            fields[name] = {
                "required": field_info.is_required(),
                "label": label,
            }
        return IntentResult(was_intent_successful=True, data=fields)

    def _validated_save(self, entity) -> IntentResult:
        """Hook for subclasses to add domain validation before saving."""
        return self.save(entity)

    def _apply_nested(self, entity, nested_raw: dict):
        """Update or create nested relationship objects on an existing entity."""
        for field, raw in nested_raw.items():
            if raw is None:
                # Explicit null → clear the relationship
                setattr(entity, field, None)
                setattr(entity, f"{field}_id", None)
                continue
            model_cls = self.__save_nested__[field]
            existing = getattr(entity, field, None)
            if existing:
                for k, v in raw.items():
                    if k != "id" and not k.startswith("_"):
                        setattr(existing, k, v)
            else:
                clean = {k: v for k, v in raw.items() if k != "id" and not k.startswith("_")}
                setattr(entity, field, model_cls(**clean))

    def _build_nested(self, nested_raw: dict) -> dict:
        """Construct nested objects for a new entity."""
        result = {}
        for field, raw in nested_raw.items():
            if not raw:
                continue
            model_cls = self.__save_nested__[field]
            clean = {k: v for k, v in raw.items() if k != "id" and not k.startswith("_")}
            result[field] = model_cls(**clean)
        return result
