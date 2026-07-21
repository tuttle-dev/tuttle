"""Time-tracking data aggregation and serialization.

Converts pandas DataFrames (the in-memory time-tracking store) into
JSON-safe dicts suitable for the frontend calendar view, event lists,
and summary panels.
"""

import calendar as cal_mod
import datetime
from typing import Optional

from pandas import DataFrame

from ...timetracking import (
    DEFAULT_WORKDAY_HOURS,
    event_hours,
    sum_hours_by_tag,
    total_event_hours,
)


def df_to_records(df: DataFrame, tag_to_workday: Optional[dict] = None) -> list:
    """Convert a time-tracking DataFrame to a list of JSON-safe dicts.

    Each record includes ``is_future`` indicating whether the event is
    in the future (planned allocation) vs the past (tracked time).
    """
    if df is None or df.empty:
        return []
    tag_to_workday = tag_to_workday or {}
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    records = []
    for idx, row in df.iterrows():
        begin = idx
        begin_dt = begin if isinstance(begin, datetime.datetime) else None
        if hasattr(begin, "isoformat"):
            begin = begin.isoformat()
        end = row.get("end")
        if hasattr(end, "isoformat"):
            end = end.isoformat()
        tag = str(row.get("tag", ""))
        workday = tag_to_workday.get(tag, DEFAULT_WORKDAY_HOURS)
        dur_hours = event_hours(row, workday)
        if begin_dt is not None:
            cmp_dt = begin_dt if begin_dt.tzinfo else begin_dt.replace(tzinfo=datetime.timezone.utc)
            is_future = cmp_dt >= now
        else:
            is_future = False
        records.append(
            {
                "begin": str(begin),
                "end": str(end) if end is not None else None,
                "duration_hours": round(dur_hours, 2),
                "title": str(row.get("title", "")),
                "tag": str(row.get("tag", "")),
                "description": str(row.get("description", "") or ""),
                "all_day": bool(row.get("all_day", False)),
                "date": str(begin)[:10],
                "is_future": is_future,
            }
        )
    return records


def build_calendar_data(
    df: DataFrame,
    year: int,
    month: int,
    project_tag: Optional[str] = None,
    tag_to_title: Optional[dict] = None,
    tag_to_workday: Optional[dict] = None,
) -> dict:
    """Build a month-view calendar payload from a time-tracking DataFrame.

    Returns a dict with ``events``, ``projects`` (unique tags with hours),
    ``days`` (per-day aggregation), and ``summary`` (totals).
    """
    tag_to_title = tag_to_title or {}
    tag_to_workday = tag_to_workday or {}
    start = datetime.date(year, month, 1)
    _, last_day = cal_mod.monthrange(year, month)
    end = datetime.date(year, month, last_day)

    mask = (df.index.date >= start) & (df.index.date <= end)
    month_df = df[mask]
    if project_tag:
        month_df = month_df[month_df["tag"] == project_tag]

    events = df_to_records(month_df, tag_to_workday)

    by_tag = {t: round(h, 1) for t, h in sum_hours_by_tag(month_df, tag_to_workday).items()}
    count_by_tag = month_df.groupby("tag").size().to_dict()
    projects = [
        {
            "tag": t,
            "title": tag_to_title.get(t, t),
            "hours": h,
            "event_count": int(count_by_tag.get(t, 0)),
        }
        for t, h in sorted(by_tag.items(), key=lambda x: -x[1])
    ]

    days: dict = {}
    for idx, row in month_df.iterrows():
        d = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
        if d not in days:
            days[d] = {
                "date": d,
                "hours": 0.0,
                "all_day_count": 0,
                "tags": [],
                "count": 0,
            }
        is_all_day = bool(row.get("all_day", False))
        if is_all_day:
            days[d]["all_day_count"] += 1
        else:
            dur = row.get("duration")
            h = dur.total_seconds() / 3600 if hasattr(dur, "total_seconds") else 0
            days[d]["hours"] = round(days[d]["hours"] + h, 2)
        days[d]["count"] += 1
        tag = str(row.get("tag", ""))
        if tag and tag not in days[d]["tags"]:
            days[d]["tags"].append(tag)

    total_hours = total_event_hours(month_df, tag_to_workday) if len(month_df) else 0

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if hasattr(month_df.index, "tz") and month_df.index.tz is not None:
        future_mask = month_df.index >= now
    else:
        future_mask = month_df.index >= now.replace(tzinfo=None)
    future_df = month_df[future_mask]
    planned_hours = total_event_hours(future_df, tag_to_workday) if len(future_df) else 0

    return {
        "year": year,
        "month": month,
        "first_weekday": start.weekday(),
        "days_in_month": last_day,
        "events": events,
        "projects": projects,
        "days": days,
        "summary": {
            "total_events": len(month_df),
            "total_hours": total_hours,
            "planned_hours": planned_hours,
            "planned_events": int(future_mask.sum()),
        },
    }


def build_summary(
    df: DataFrame,
    tag_to_title: dict,
    project_tag: Optional[str] = None,
    tag_to_workday: Optional[dict] = None,
) -> dict:
    """Build a time-tracking summary: totals and per-project breakdown.

    *tag_to_title* maps project tags to human-readable titles.
    When *project_tag* is provided, totals and project list are filtered to
    that tag only.
    """
    if df is None or df.empty:
        return {"total_events": 0, "total_hours": 0, "projects": []}

    if project_tag:
        df = df[df["tag"] == project_tag]
        if df.empty:
            return {"total_events": 0, "total_hours": 0, "projects": []}

    tag_to_workday = tag_to_workday or {}
    total_hours = total_event_hours(df, tag_to_workday)
    by_tag = {t: round(h, 1) for t, h in sum_hours_by_tag(df, tag_to_workday).items()}
    project_summaries = []
    for tag, hours in sorted(by_tag.items(), key=lambda x: -x[1]):
        project_summaries.append(
            {
                "tag": tag,
                "title": tag_to_title.get(tag, tag),
                "hours": hours,
                "event_count": int((df["tag"] == tag).sum()),
            }
        )
    return {
        "total_events": len(df),
        "total_hours": round(total_hours, 1),
        "projects": project_summaries,
    }


def merge_dataframes(existing: Optional[DataFrame], new_df: DataFrame) -> DataFrame:
    """Merge *new_df* into *existing*, deduplicating by index."""
    if existing is not None and not existing.empty:
        import pandas

        combined = pandas.concat([existing, new_df])
        combined = combined[~combined.index.duplicated(keep="last")]
        return combined
    return new_df
