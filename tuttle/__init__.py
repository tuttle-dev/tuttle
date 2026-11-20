"""Top-level package for tuttle."""

__version__ = "5.5.0"

try:
    from . import app  # noqa: F401
except ImportError:
    pass

from . import (  # noqa: F401
    calendar,
    invoicing,
    mail,
    model,
    rendering,
    tax,
    time,
    timetracking,
)
