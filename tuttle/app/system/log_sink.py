"""In-memory ring buffer sink for loguru — exposes recent logs to the UI."""

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import List

_MAX_ENTRIES = 200

_buffer: deque = deque(maxlen=_MAX_ENTRIES)
_lock = Lock()


def sink(message):
    """Loguru sink function. Captures structured log records."""
    record = message.record
    entry = {
        "ts": record["time"].astimezone(timezone.utc).isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    if record["exception"] is not None:
        entry["exception"] = str(record["exception"].value)
    with _lock:
        _buffer.append(entry)


def get_recent(limit: int = 100, level: str | None = None) -> List[dict]:
    """Return the most recent log entries, newest first."""
    with _lock:
        entries = list(_buffer)
    entries.reverse()
    if level:
        level_upper = level.upper()
        entries = [e for e in entries if e["level"] == level_upper]
    return entries[:limit]


def clear() -> None:
    with _lock:
        _buffer.clear()
