"""Pandera schemata."""
from pandera import SchemaModel, DataFrameSchema, Field, Column, DateTime, Timedelta


time_tracking = DataFrameSchema(
    columns={
        "begin": Column(DateTime, nullable=True),
        "end": Column(DateTime, nullable=True),
        "title": Column(str, nullable=True),
        "tag": Column(str),
        "description": Column(str, nullable=True),
        "duration": Column(Timedelta),
    }
)
