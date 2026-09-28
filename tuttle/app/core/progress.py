"""Progress events pushed to the UI while a long-running RPC call is in flight.

The transport (``tuttle.rpc_server``) installs an emitter at startup; without
one (tests, CLI) ``emit`` is a no-op.
"""

from typing import Any, Callable, Dict, Optional

_emitter: Optional[Callable[[Dict[str, Any]], None]] = None


def set_emitter(fn: Optional[Callable[[Dict[str, Any]], None]]) -> None:
    global _emitter
    _emitter = fn


def emit(topic: str, **payload: Any) -> None:
    if _emitter is not None:
        _emitter({"topic": topic, **payload})
