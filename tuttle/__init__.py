"""Top-level package for tuttle."""

__version__ = "4.0.0"

try:
    from . import app  # noqa: F401
except ImportError:
    pass

from . import (  # noqa: F401
    banking,
    calendar,
    invoicing,
    model,
    tax,
    timetracking,
    dataviz,
    time,
    rendering,
    os_functions,
    mail,
)
