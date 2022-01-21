"""Calendar integration."""

from pathlib import Path

import ics
import pyicloud
import getpass
import pandas
import datetime

from pandera.typing import DataFrame
from pandera import check_io

from . import schema


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


class FileCalendar(Calendar):
    """An .ics file based calendar."""

    def __init__(self, path, name: str):
        super().__init__(name)
        self.path = path
        with open(self.path, "r") as cal_file:
            self.ical = ics.Calendar(cal_file.read())

    def to_data(self) -> DataFrame:
        """Convert ics.Calendar to pandas.DataFrame"""
        event_data = pandas.DataFrame(
            [
                (
                    event.name,
                    # TODO: handle time zones
                    pandas.to_datetime(event.begin.datetime).tz_convert("CET"),
                    pandas.to_datetime(event.end.datetime).tz_convert("CET"),
                )
                for event in self.ical.events
            ],
            columns=["title", "begin", "end"],
        )
        event_data["duration"] = event_data["end"] - event_data["begin"]
        # event_data["time"] = event_data["begin"]
        event_data = event_data.set_index("begin")
        return event_data


class ICloudCalendar(CloudCalendar):
    """iCloud calendar."""

    def __init__(
        self,
        icloud: pyicloud.PyiCloudService,
        name: str,
    ):
        super().__init__(name)
        self.icloud = icloud
        calendars = icloud.calendar.calendars()
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

    def get_raw_data(self) -> DataFrame:
        """Convert iCloud calendar events to DataFrame"""
        all_events = self.icloud.calendar.events(
            from_dt=datetime.datetime(1, 1, 1), to_dt=datetime.date.today()
        )
        event_data_raw = pandas.DataFrame(all_events)
        return event_data_raw

    def to_data(self) -> DataFrame:
        """Convert iCloud calendar events to time tracking data format."""

        event_data_raw = self.get_raw_data()
        guid = self.guid
        event_data = event_data_raw.query("pGuid == @guid")
        timetracking_data = pandas.DataFrame().assign(
            **{
                "begin": event_data["startDate"].apply(parse_pyicloud_datetime),
                "end": event_data["endDate"].apply(parse_pyicloud_datetime),
                "title": event_data["title"],
                # TODO: extract tag
                "tag": event_data["title"],
                "description": event_data["description"],
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
