"""Top-level package for tuttle."""

__author__ = """Christian Staudt"""
__version__ = "0.2.1"

from . import (
    banking,
    calendar,
    cloud,
    controller,
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


import pandas

pandas.set_option("display.max_columns", 100)
