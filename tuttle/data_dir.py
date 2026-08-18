"""Resolve the root data directory for all Tuttle user data.

Production (PyInstaller-frozen build): ``~/.tuttle``.
Everything else — ``uv run``, tests, an unfrozen dev Electron build, an
agent poking at the core directly — defaults to ``~/.tuttle-dev`` instead.
Only a real end user's installed app is frozen, so this means source
checkouts of this repo can never silently read or write someone's real
data just because a script forgot to set ``TUTTLE_DATA_DIR``. Set the env
var explicitly (e.g. after ``just sync-data``) to point dev tooling at a
copy of the real data on purpose.
"""

import os
import sys
from pathlib import Path

_DEFAULT = Path.home() / ".tuttle"
_DEFAULT_DEV = Path.home() / ".tuttle-dev"


def get_data_dir() -> Path:
    """Return the root data directory, creating it if necessary."""
    env = os.environ.get("TUTTLE_DATA_DIR")
    if env:
        d = Path(env)
    elif getattr(sys, "frozen", False):
        d = _DEFAULT
    else:
        d = _DEFAULT_DEV
    d.mkdir(parents=True, exist_ok=True)
    return d
