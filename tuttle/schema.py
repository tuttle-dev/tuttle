"""Pandera schemata."""
from pandera import (
    SchemaModel,
    DataFrameSchema,
    Column,
    Index,
    DateTime,
    Timedelta,
    String,
)


time_tracking = DataFrameSchema(
    index=Index(DateTime, name="begin", allow_duplicates=True),
    columns={
        # "begin": Column(DateTime, nullable=True),
        "end": Column(DateTime, nullable=True),
        "title": Column(String, nullable=True),
        "tag": Column(String),
        "description": Column(String, nullable=True),
        "duration": Column(Timedelta),
    },
)