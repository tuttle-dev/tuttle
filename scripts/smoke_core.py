"""Smoke-test the frozen PyInstaller core binary.

Spawns the actual ``dist/tuttle-rpc`` binary and verifies that every RPC
domain (a ``tuttle/app/<domain>/intent.py`` on disk) is bundled and importable
in the frozen build. This catches the class of release regression where a
dynamically-imported intent module is silently dropped from the binary,
producing ``No module named 'tuttle.app.<domain>'`` only in the distributed app.

How it works: the dispatcher imports ``tuttle.app.<domain>.intent`` on the first
call to any method of that domain. We send each domain a sentinel method name:

    - missing from bundle  -> error contains "No module named 'tuttle.app.<domain>'"  (FAIL)
    - bundled & importable -> error contains "No handler for ..."                       (PASS)

No database or valid parameters are required.

All probes are written up front and stdin is then closed (EOF). We never
interleave a write with a blocking read, because the frozen server iterates
``for line in sys.stdin`` which does read-ahead buffering — on Windows it does
not yield a line until the buffer fills or EOF, so a write/read ping-pong
deadlocks there. Writing everything then reading after EOF is deadlock-free and
bounded by a hard timeout.

Usage:
    uv run python scripts/smoke_core.py
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "tuttle" / "app"
PROBE_METHOD = "__smoke_probe__"
TIMEOUT_SECONDS = 180


def discover_domains() -> list[str]:
    """Names of every directory under tuttle/app that has intent.py (except core)."""
    return sorted(p.parent.name for p in APP_DIR.glob("*/intent.py") if p.parent.name != "core")


def core_binary() -> Path:
    exe = "tuttle-rpc.exe" if sys.platform.startswith("win") else "tuttle-rpc"
    return REPO_ROOT / "dist" / "tuttle-rpc" / exe


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

    print(f"Probing {len(domains)} domains against {binary.name}: {domains}")

    # Build all probe requests; id maps back to domain.
    requests = "".join(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": i,
                "method": f"{domain}.{PROBE_METHOD}",
                "params": {},
            }
        )
        + "\n"
        for i, domain in enumerate(domains, start=1)
    )
    id_to_domain = {i: domain for i, domain in enumerate(domains, start=1)}

    proc = subprocess.Popen(
        [str(binary)],
        cwd=str(binary.parent),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        stdout, _stderr = proc.communicate(input=requests, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        print(
            f"ERROR: core did not respond within {TIMEOUT_SECONDS}s — killed.",
            file=sys.stderr,
        )
        return 1

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

    failures: list[str] = []
    for i, domain in id_to_domain.items():
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
        print("\nSMOKE TEST FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print(
            "\nA domain reachable via the dispatcher is missing from the frozen "
            "build. Check tuttle-rpc.spec (collect_submodules) and that the "
            "domain directory has an __init__.py.",
            file=sys.stderr,
        )
        return 1

    print(f"\nSMOKE TEST PASSED: all {len(domains)} domains bundled & importable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
