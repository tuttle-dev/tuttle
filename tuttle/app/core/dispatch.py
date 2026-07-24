"""Convention-based JSON-RPC dispatcher.

Every RPC call ``domain.method_name`` is resolved to an intent method:

    tuttle.app.{domain}.intent.{Domain}Intent.{method_name}

Method resolution tries suffixes in order: ``_from_dict``, exact, ``_as_map``.
Params are bound via ``inspect.signature`` with single-value fallback.
Return values are serialised through ``dump()`` (which honours ``to_rpc_dict()``).
"""

import importlib
import inspect
from typing import Any, Callable, Dict

from .rpc_utils import dump, register_reset, unwrap

# ---------------------------------------------------------------------------
# Intent singleton cache
# ---------------------------------------------------------------------------

_intents: Dict[str, Any] = {}


def _clear_intents():
    _intents.clear()


register_reset(_clear_intents)


def _get_intent(domain: str):
    if domain not in _intents:
        mod_path = f"tuttle.app.{domain}.intent"
        mod = importlib.import_module(mod_path)
        # Find the Intent subclass defined in this module (not imported ones)
        candidates = [
            obj
            for name, obj in inspect.getmembers(mod, inspect.isclass)
            if name.endswith("Intent") and obj.__module__ == mod.__name__
        ]
        if len(candidates) != 1:
            raise AttributeError(f"Expected exactly 1 *Intent class in {mod_path}, found {[c.__name__ for c in candidates]}")
        _intents[domain] = candidates[0]()
    return _intents[domain]


# ---------------------------------------------------------------------------
# Method resolution
# ---------------------------------------------------------------------------

_SUFFIXES = ("_from_dict", "", "_as_map")


def _resolve_method(intent, method_name: str) -> Callable | None:
    for suffix in _SUFFIXES:
        fn = getattr(intent, method_name + suffix, None)
        if fn is not None and callable(fn):
            return fn
    return None


# ---------------------------------------------------------------------------
# Introspective param binding
# ---------------------------------------------------------------------------


def _call(fn: Callable, params: dict):
    sig = inspect.signature(fn)
    positional = [
        p
        for name, p in sig.parameters.items()
        if name != "self"
        and p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]

    if not positional:
        return fn()

    try:
        return fn(**params)
    except TypeError:
        pass

    if len(positional) == 1:
        p = positional[0]
        if p.name in params:
            return fn(params[p.name])
        if len(params) == 1:
            return fn(next(iter(params.values())))
        return fn(params)

    kwargs = {}
    for p in positional:
        if p.name in params:
            kwargs[p.name] = params[p.name]
        elif p.default is not inspect.Parameter.empty:
            pass
        else:
            raise TypeError(f"Missing required param '{p.name}' for {fn.__name__}")
    return fn(**kwargs)


# ---------------------------------------------------------------------------
# Result serialisation
# ---------------------------------------------------------------------------


def _serialize(result) -> dict:
    if hasattr(result, "was_intent_successful"):
        if not result.was_intent_successful:
            return unwrap(result)
        warning = getattr(result, "warning", "") or None
        data = result.data
    else:
        warning = None
        data = result
    return {"ok": True, "data": dump(data), "error": None, "warning": warning}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def dispatch(method: str, params: dict) -> dict:
    dot = method.find(".")
    if dot < 0:
        raise ValueError(f"Method must be 'domain.name', got: {method}")
    domain, method_name = method[:dot], method[dot + 1 :]

    intent = _get_intent(domain)
    fn = _resolve_method(intent, method_name)
    if fn is None:
        raise ValueError(f"No handler for '{method}'")

    return _serialize(_call(fn, params))
