"""Calendar integration."""
from typing import Optional

from pathlib import Path
import io
import re

from loguru import logger
import ics
import icloudpy
import getpass
import pandas
import datetime

from pandera.typing import DataFrame
from pandera import check_io
from pandas import DataFrame

from . import schema


def extract_hashtag(string) -> str:
    """Extract the first hashtag from a string."""
    match = re.search(r"(#\S+)", string)
    if match:
        return match.group(1)
    else:
        return ""


def parse_pyicloud_datetime(dt_list):
    """Parse the dates returned by pyicloud."""
    _, year, month, day, hour, minute, _ = dt_list
    return datetime.datetime(year, month, day, hour, minute)


class Calendar:
    """Abstract base class for calendars."""

    def __init__(self, name: str):
        self.name = name

    @check_io(out=schema.time_tracking)
    def to_data(self) -> DataFrame:
        """Convert events to dataframe."""
        raise NotImplementedError("Abstract base class")


class CloudCalendar(Calendar):
    """Abstract base class for calendars in the cloud."""

    pass


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
            raise ValueError(
                "Either a path to or the content of an .ics file must be passed."
            )

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
        # TODO: handle errors from data transformation here
        event_data = pandas.DataFrame(
            [
                (
                    event.name,
                    event.description,
                    pandas.to_datetime(event.begin.datetime).tz_convert("CET"),
                    pandas.to_datetime(event.end.datetime).tz_convert("CET"),
                    event.all_day,
                    # TODO: handle time zones
                    # pandas.to_datetime(event.begin.datetime).tz_convert("CET"),
                    # pandas.to_datetime(event.end.datetime).tz_convert("CET"),
                )
                for event in self.ical.events
            ],
            columns=["title", "description", "begin", "end", "all_day"],
        )
        event_data["duration"] = event_data["end"] - event_data["begin"]
        # apply the function extract_hashtag to the column title to derive the column tag
        event_data["tag"] = event_data["title"].apply(extract_hashtag)
        # event_data["time"] = event_data["begin"]
        event_data = event_data.set_index("begin")
        return event_data


class ICloudCalendar(CloudCalendar):
    """iCloud calendar."""

    def __init__(
        self,
        icloud_connector: icloudpy.ICloudPyService,
        name: str,
    ):
        super().__init__(name)
        self.icloud = icloud_connector
        calendars = icloud_connector.calendar.calendars()
        calendars_df = pandas.DataFrame(calendars)
        cal_to_guid = dict(
            (cal_name, guid)
            for (cal_name, guid) in zip(calendars_df["title"], calendars_df["guid"])
        )
        try:
            # calendar id
            self.guid = cal_to_guid[self.name]
        except KeyError:
            raise ValueError(f"iCloud calendar {self.name} not found")

    def to_raw_data(self) -> DataFrame:
        """Convert iCloud calendar events to DataFrame"""
        all_events = self.icloud.calendar.events(
            from_dt=datetime.datetime(1, 1, 1), to_dt=datetime.datetime(2100, 1, 1)
        )
        event_data_raw = pandas.DataFrame(all_events)
        return event_data_raw

    @check_io(out=schema.time_tracking)
    def to_data(self) -> DataFrame:
        """Convert iCloud calendar events to time tracking data format."""

        event_data_raw = self.to_raw_data()
        guid = self.guid
        event_data = event_data_raw.query("pGuid == @guid")
        timetracking_data = pandas.DataFrame().assign(
            **{
                "begin": event_data["startDate"].apply(parse_pyicloud_datetime),
                "end": event_data["endDate"].apply(parse_pyicloud_datetime),
                "title": event_data["title"],
                # TODO: extract tag
                "tag": extract_hashtag(event_data["title"]),
                "description": event_data["description"],
                "all_day": event_data["allDay"],
            }
        )
        # TODO: handle timezones
        timetracking_data = timetracking_data.assign(
            **{
                "duration": event_data["duration"].apply(
                    lambda m: datetime.timedelta(minutes=m)
                )
            }
        )
        timetracking_data = timetracking_data.set_index("begin")
        return timetracking_data


class GoogleCalendar(CloudCalendar):
    """Google calendar"""

    def to_data(self) -> DataFrame:
        raise NotImplementedError("TODO")
