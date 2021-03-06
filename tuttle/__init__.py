"""Top-level package for tuttle."""

__author__ = """Christian Staudt"""
__version__ = "0.0.4"

from . import (
    app,
    banking,
    calendar,
    cloud,
    context,
    invoicing,
    model,
    tax,
    timetracking,
    dataviz,
    time,
    rendering,
    view,
)


import pandas

pandas.set_option("display.max_columns", 100)
