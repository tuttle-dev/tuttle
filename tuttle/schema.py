"""Pandera schemata — time tracking schemas delegated to calendula."""

from calendula.schema import time_planning, time_tracking

from pandera.pandas import (
    Column,
    DataFrameSchema,
    DateTime,
    Decimal,
    String,
)

ledger = DataFrameSchema(
    columns={
        "date": Column(DateTime),
        "name": Column(String),
        "purpose": Column(String),
        "account": Column(String),
        "bank": Column(String),
        "amount": Column(Decimal),
    },
)

__all__ = [
    "time_tracking",
    "time_planning",
    "ledger",
]
