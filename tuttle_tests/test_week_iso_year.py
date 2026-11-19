"""A week bucket carries the ISO year its week number counts in."""

import datetime

from tuttle.forecasting import revenue_series


def _bucket(series, start: datetime.date) -> dict:
    return next(b for b in series["buckets"] if b["bucket"] == start.isoformat())


def test_the_week_of_new_year_is_the_first_week_of_the_new_year():
    series = revenue_series([], [], None, "week", today=datetime.date(2026, 1, 2))

    last_week = _bucket(series, datetime.date(2025, 12, 22))
    new_year = _bucket(series, datetime.date(2025, 12, 29))
    assert (last_week["label"], last_week["year"]) == ("W52", 2025)
    assert (new_year["label"], new_year["year"]) == ("W01", 2026)
    assert new_year["is_year_start"]
    assert not last_week["is_year_start"]


def test_a_53rd_week_stays_in_its_year():
    """2026 has 53 ISO weeks; the one that reaches into January 2027 is W53 of 2026."""
    series = revenue_series([], [], None, "week", today=datetime.date(2027, 1, 1))

    w53 = _bucket(series, datetime.date(2026, 12, 28))
    assert (w53["label"], w53["year"]) == ("W53", 2026)
    assert _bucket(series, datetime.date(2027, 1, 4))["is_year_start"]
