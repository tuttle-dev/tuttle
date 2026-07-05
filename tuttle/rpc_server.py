"""JSON-RPC 2.0 stdin/stdout transport.

This module does exactly two things:
    1. Read newline-delimited JSON-RPC requests from stdin.
    2. Route them through ``tuttle.app.core.dispatch.dispatch`` and write
       the JSON-RPC response to stdout.

All domain logic, serialisation, and intent lifecycle live elsewhere.

Usage::

    python -m tuttle.rpc_server
"""

import json
import os
import signal
import sys
import threading
import traceback
from typing import Any, Dict

from loguru import logger

logger.remove()
logger.add(sys.stderr, level="DEBUG")

from tuttle.app.system.log_sink import sink as _log_sink  # noqa: E402

logger.add(_log_sink, level="DEBUG")


def _start_parent_watchdog(interval: float = 2.0):
    """Exit if the parent process (Electron) disappears.

    Polls os.getppid(); when it changes to 1 (re-parented to init/launchd)
    the parent has died and we must not linger as an orphan.
    """
    parent_pid = os.getppid()

    def _watch():
        while True:
            if os.getppid() != parent_pid:
                logger.warning("Parent process gone — shutting down")
                os.kill(os.getpid(), signal.SIGTERM)
                return
            threading.Event().wait(interval)

    t = threading.Thread(target=_watch, daemon=True)
    t.start()


def main():
    from tuttle.app.core.dispatch import dispatch

    _start_parent_watchdog()
    logger.info("Tuttle RPC server starting…")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        req_id = None
        response: Dict[str, Any]
        try:
            request = json.loads(line)
            req_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {})

            result = dispatch(method, params)

            response = {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as exc:
            logger.exception(f"RPC error: {exc}")
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": str(exc),
                    "data": traceback.format_exc(),
                },
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
