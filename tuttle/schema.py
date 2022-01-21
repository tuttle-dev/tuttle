"""Pandera schemata."""
from pandera import SchemaModel, DataFrameSchema, Field, Column, DateTime, Timedelta


time_tracking = DataFrameSchema(
    columns={
        "begin": Column(DateTime),
        "end": Column(DateTime),
        "title": Column(str),
        "tag": Column(str),
        "duration": Column(Timedelta),
    }
)
