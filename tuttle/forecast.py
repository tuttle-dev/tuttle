"""Income forecasting functionality."""

import pandas

from .model import Project


def eval_time_allocation(
    source,
):
    if issubclass(type(source), Calendar):
        cal = source
        timetracking_data = cal.to_data()
    elif isinstance(source, pandas.DataFrame):
        timetracking_data = source
        schema.time_tracking.validate(timetracking_data)
