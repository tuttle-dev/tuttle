"""Calendar integration."""

import calendar
import datetime
import io
import re
from typing import Optional

import ics
import pandas
from pandas import DataFrame
from pandera import check_io

from . import schema


def extract_hashtag(string) -> str:
    """Extract the first hashtag from a string."""
    match = re.search(r"(#\S+)", string)
    if match:
        return match.group(1)
    else:
        return ""


class Calendar:
    """Abstract base class for calendars."""

    def __init__(self, name: str):
        self.name = name

    @check_io(out=schema.time_tracking)
    def to_data(self) -> DataFrame:
        """Convert events to dataframe."""
        raise NotImplementedError("Abstract base class")


class ICSCalendar(Calendar):
    """An ICS data format based calendar."""

    def __init__(
        self,
        name: str,
        path: Optional[str] = None,
        content: Optional[bytes] = None,
        ics_calendar: Optional[ics.Calendar] = None,
    ):
        super().__init__(name)
        if path is not None:
            self.path = path
            with open(self.path, "r") as cal_file:
                self.ical = ics.Calendar(cal_file.read())
        elif content is not None:
            self.content = content
            with io.TextIOWrapper(io.BytesIO(content), encoding="utf-8") as cal_file:
                self.ical = ics.Calendar(cal_file.read())
        elif ics_calendar is not None:
            self.ical = ics_calendar
        else:
            raise ValueError("Either a path to or the content of an .ics file must be passed.")

    def to_raw_data(self) -> DataFrame:
        """Convert .ics calendar events to DataFrame"""
        events = [event for event in self.ical.events]
        event_data_raw = pandas.DataFrame(
            [tuple(event.__dict__.values()) for event in events],
            columns=list(events[0].__dict__.keys()),
        )
        return event_data_raw

    @check_io(out=schema.time_tracking)
    def to_data(self) -> DataFrame:
        """Convert ics.Calendar to pandas.DataFrame"""
        rows = []
        for event in self.ical.events:
            begin = pandas.to_datetime(event.begin.datetime).tz_convert("CET")
            end = pandas.to_datetime(event.end.datetime).tz_convert("CET")
            is_all_day = event.all_day
            title = event.name
            description = event.description

            if is_all_day and (end - begin).days > 1:
                day = begin
                while day < end:
                    day_end = day + pandas.Timedelta(days=1)
                    rows.append(
                        {
                            "begin": day,
                            "title": title,
                            "description": description,
                            "end": day_end,
                            "all_day": True,
                            "duration": pandas.Timedelta(days=1),
                            "tag": extract_hashtag(title),
                        }
                    )
                    day = day_end
            else:
                rows.append(
                    {
                        "begin": begin,
                        "title": title,
                        "description": description,
                        "end": end,
                        "all_day": is_all_day,
                        "duration": end - begin,
                        "tag": extract_hashtag(title),
                    }
                )

        event_data = pandas.DataFrame(rows)
        event_data = event_data.set_index("begin")
        return event_data


def get_month_start_end(month_str):
    # Parse the string into a datetime object
    dt = datetime.datetime.strptime(month_str, "%B %Y")

    # Get the date information from the datetime object
    year, month = dt.date().year, dt.date().month

    # Get the start and end dates of the month
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, calendar.monthrange(year, month)[1])

    return start_date, end_date
