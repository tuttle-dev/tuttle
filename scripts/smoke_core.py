"""Smoke-test the frozen PyInstaller core binary.

Spawns the actual ``dist/tuttle-rpc`` binary and runs two independent checks:

1. **Domain probes** — every RPC domain (a ``tuttle/app/<domain>/intent.py`` on
   disk) is bundled and importable. Catches the regression where a
   dynamically-imported intent module is silently dropped from the binary,
   producing ``No module named 'tuttle.app.<domain>'`` only in the
   distributed app.

2. **Lifecycle** — the startup sequence actually works end to end against a
   throwaway data directory: create a user (runs an Alembic migration on a new
   database), then re-launch the binary and confirm ``db.ensure`` adopts the
   existing user. Import-time gaps in code the analyzer cannot trace only
   surface when the code runs; a probe that never touches a database misses
   them. In v4.3.0 ``logging.config`` was absent from the bundle, so every
   migration failed, ``db.ensure`` aborted before selecting a database, and the
   app started with "No user" against an empty default DB — with the domain
   probes passing.

How the domain probes work: the dispatcher imports ``tuttle.app.<domain>.intent``
on the first call to any method of that domain. We send each domain a sentinel
method name:

    - missing from bundle  -> error contains "No module named 'tuttle.app.<domain>'"  (FAIL)
    - bundled & importable -> error contains "No handler for ..."                       (PASS)

All requests in a run are written up front and stdin is then closed (EOF). We
never interleave a write with a blocking read, because the frozen server
iterates ``for line in sys.stdin`` which does read-ahead buffering — on Windows
it does not yield a line until the buffer fills or EOF, so a write/read
ping-pong deadlocks there. Writing everything then reading after EOF is
deadlock-free and bounded by a hard timeout. Anything needing state from an
earlier call is therefore a separate run, which also mirrors how a real relaunch
behaves.

Usage:
    uv run python scripts/smoke_core.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "tuttle" / "app"
PROBE_METHOD = "__smoke_probe__"
TIMEOUT_SECONDS = 180
SMOKE_USER_NAME = "Smoke Test User"


def discover_domains() -> list[str]:
    """Names of every directory under tuttle/app that has intent.py (except core)."""
    return sorted(p.parent.name for p in APP_DIR.glob("*/intent.py") if p.parent.name != "core")


def core_binary() -> Path:
    exe = "tuttle-rpc.exe" if sys.platform.startswith("win") else "tuttle-rpc"
    return REPO_ROOT / "dist" / "tuttle-rpc" / exe


def run_calls(binary: Path, calls: list[tuple[str, dict]], data_dir: Path | None = None) -> dict[int, dict]:
    """Send every call to a fresh core process, then read replies after EOF.

    Returns responses keyed by their 1-based position in *calls*.
    """
    requests = "".join(
        json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n"
        for i, (method, params) in enumerate(calls, start=1)
    )

    env = os.environ.copy()
    if data_dir is not None:
        env["TUTTLE_DATA_DIR"] = str(data_dir)

    proc = subprocess.Popen(
        [str(binary)],
        cwd=str(binary.parent),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    try:
        stdout, _stderr = proc.communicate(input=requests, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise TimeoutError(f"core did not respond within {TIMEOUT_SECONDS}s — killed")

    responses: dict[int, dict] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            resp = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(resp, dict) and "id" in resp:
            responses[resp["id"]] = resp
    return responses


def check_domains(binary: Path, domains: list[str]) -> list[str]:
    """Every dispatcher-reachable domain is bundled and importable."""
    print(f"Probing {len(domains)} domains against {binary.name}: {domains}")

    try:
        responses = run_calls(binary, [(f"{d}.{PROBE_METHOD}", {}) for d in domains])
    except TimeoutError as exc:
        return [f"domain probes: {exc}"]

    failures: list[str] = []
    for i, domain in enumerate(domains, start=1):
        resp = responses.get(i)
        if resp is None:
            failures.append(f"{domain}: no response from core")
            continue
        blob = json.dumps(resp)
        if "No module named" in blob and f"tuttle.app.{domain}" in blob:
            failures.append(f"{domain}: NOT bundled in frozen binary -> {blob}")
        else:
            print(f"  ok   {domain}")

    if failures:
        failures.append(
            "A domain reachable via the dispatcher is missing from the frozen "
            "build. Check tuttle-rpc.spec (collect_submodules) and that the "
            "domain directory has an __init__.py."
        )
    return failures


def _payload(resp: dict | None) -> tuple[dict | None, str | None]:
    """Split a JSON-RPC reply into (result payload, error message)."""
    if resp is None:
        return None, "no response from core"
    if resp.get("error"):
        return None, str(resp["error"].get("message") or resp["error"])
    result = resp.get("result") or {}
    if not result.get("ok"):
        return None, str(result.get("error") or "call reported ok=false")
    return result, None


def check_lifecycle(binary: Path) -> list[str]:
    """The startup sequence works end to end against a throwaway data dir."""
    print("\nExercising startup lifecycle (db.ensure, user creation, migration)")
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="tuttle-smoke-") as tmp:
        data_dir = Path(tmp)

        try:
            first = run_calls(
                binary,
                [
                    ("db.ensure", {}),
                    ("users.create", {"params": {"name": SMOKE_USER_NAME}}),
                    ("users.get_active", {}),
                ],
                data_dir=data_dir,
            )
        except TimeoutError as exc:
            return [f"lifecycle: {exc}"]

        for step, method in enumerate(["db.ensure", "users.create", "users.get_active"], start=1):
            _result, error = _payload(first.get(step))
            if error:
                failures.append(f"{method} (first launch): {error}")

        active, error = _payload(first.get(3))
        if not error:
            user = (active or {}).get("data")
            if not user:
                failures.append("users.get_active (first launch): no active user after users.create")
            elif user.get("name") != SMOKE_USER_NAME:
                failures.append(f"users.get_active (first launch): unexpected user {user.get('name')!r}")

        # Relaunch: db.ensure must migrate and adopt the existing user database.
        try:
            second = run_calls(
                binary,
                [("db.ensure", {}), ("users.get_active", {})],
                data_dir=data_dir,
            )
        except TimeoutError as exc:
            return failures + [f"lifecycle relaunch: {exc}"]

        _result, error = _payload(second.get(1))
        if error:
            failures.append(f"db.ensure (relaunch): {error}")

        active, error = _payload(second.get(2))
        if error:
            failures.append(f"users.get_active (relaunch): {error}")
        else:
            user = (active or {}).get("data")
            if not user or user.get("name") != SMOKE_USER_NAME:
                failures.append(
                    "users.get_active (relaunch): existing user was not adopted — "
                    f"got {user!r}. The app would start with 'No user' against an empty database."
                )

    if not failures:
        print("  ok   user created, migrated, and adopted on relaunch")
    return failures


def main() -> int:
    binary = core_binary()
    if not binary.exists():
        print(f"ERROR: core binary not found at {binary}", file=sys.stderr)
        print(
            "Build it first: uv run pyinstaller --clean --noconfirm tuttle-rpc.spec",
            file=sys.stderr,
        )
        return 1

    domains = discover_domains()
    if not domains:
        print("ERROR: no domains discovered under tuttle/app/", file=sys.stderr)
        return 1

    failures = check_domains(binary, domains) + check_lifecycle(binary)

    if failures:
        print("\nSMOKE TEST FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"\nSMOKE TEST PASSED: {len(domains)} domains bundled, startup lifecycle works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
