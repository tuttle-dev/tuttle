"""Top-level package for tuttle."""

__version__ = "4.3.1"

try:
    from . import app  # noqa: F401
except ImportError:
    pass

from . import (  # noqa: F401
    banking,
    calendar,
    dataviz,
    invoicing,
    mail,
    model,
    os_functions,
    rendering,
    tax,
    time,
    timetracking,
)
