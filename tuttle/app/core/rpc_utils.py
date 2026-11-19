"""Shared RPC serialisation and envelope utilities.

Generic protocol helpers — not domain logic.
"""

import datetime
from decimal import Decimal
from typing import Any, Callable, Dict

import pandas


def dump(obj: Any) -> Any:
    """Recursively convert a Python value to JSON-safe primitives.

    Models with ``RpcMixin`` get relationship-aware serialisation via
    ``to_rpc_dict()``.  Plain SQLModel/Pydantic models fall back to
    ``model_dump()`` (column fields only).
    """
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        import math

        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (str, int)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, datetime.timedelta):
        return obj.total_seconds()
    if isinstance(obj, dict):
        return {str(k): dump(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [dump(v) for v in obj]
    if isinstance(obj, pandas.DataFrame):
        return [dump(row) for row in obj.to_dict(orient="records")]
    if isinstance(obj, pandas.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pandas.Timedelta):
        return obj.total_seconds()
    if hasattr(obj, "to_rpc_dict"):
        return dump(obj.to_rpc_dict())
    if hasattr(obj, "model_dump"):
        return dump(obj.model_dump())
    if hasattr(obj, "_asdict"):
        return dump(obj._asdict())
    if hasattr(obj, "__dataclass_fields__"):
        import dataclasses

        return dump(dataclasses.asdict(obj))
    if hasattr(obj, "value"):
        return dump(obj.value)
    import numpy as np

    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        import math

        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return str(obj)


def unwrap(result) -> Dict[str, Any]:
    """Convert an IntentResult to a ``{ok, data, error, warning}`` envelope."""
    return {
        "ok": result.was_intent_successful,
        "data": dump(result.data),
        "error": result.error_msg or None,
        "warning": result.warning or None,
    }


# ---------------------------------------------------------------------------
# Intent singleton reset registry
# ---------------------------------------------------------------------------

_reset_fns: list[Callable] = []


def register_reset(fn: Callable) -> None:
    """Register a zero-arg callable that clears a domain's intent cache."""
    if fn not in _reset_fns:
        _reset_fns.append(fn)


def reset_all() -> None:
    """Invoke every registered reset callback (cross-domain cache flush)."""
    for fn in _reset_fns:
        fn()
