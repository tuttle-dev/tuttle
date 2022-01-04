"""Calendar integration."""

import ics
import pyicloud
import getpass
import pandas
import datetime

from pathlib import Path

def parse_pyicloud_datetime(dt_list):
    """Parse the dates returned by pyicloud."""
    _, year, month, day, hour, minute, _ = dt_list
    return datetime.datetime(year, month, day, hour, minute)


class Calendar:
    """Abstract base class for calendars."""
    def __init__(
        self,
        name: str
    ):
        self.name = name


class FileCalendar(Calendar):
    """An .ics file based calendar."""

    def __init__(
        self,
        path,
        name: str
    ):
        super().__init__(name)
        self.path = path
        with open(self.path, "r") as cal_file:
            self.ical = ics.Calendar(cal_file.read())


    def to_data(self) -> pandas.DataFrame:
        """Convert ics.Calendar to pandas.DataFrame"""
        event_data = pandas.DataFrame(
            [
                (
                    event.name,
                    pandas.to_datetime(event.begin.datetime).tz_convert('CET'),
                    pandas.to_datetime(event.end.datetime).tz_convert('CET'),
                ) for event in self.ical.events
            ],
            columns=["name", "begin", "end"],
        )
        event_data["duration"] = event_data["end"] - event_data["begin"]
        #event_data["time"] = event_data["begin"]
        #event_data = event_data.set_index("time")
        return event_data



class CloudCalendar(Calendar):

    def __init__(
        self,
        icloud: pyicloud.PyiCloudService,
        name: str
    ):
        super().__init__(name)
        self.icloud = icloud
        calendars = icloud.calendar.calendars()
        calendars_df = pandas.DataFrame(calendars)
        cal_to_guid = dict((cal_name, guid) for (cal_name, guid) in zip(calendars_df["title"], calendars_df["guid"]))
        try:
            # calendar id
            self.guid = cal_to_guid[self.name]
        except KeyError:
            raise ValueError(f"iCloud calendar {self.name} not found")



    def to_data(self) -> pandas.DataFrame:
        """Convert icloud calendar events to pandas.DataFrame"""

        all_events = self.icloud.calendar.events(
            from_dt=datetime.datetime(1,1,1),
            to_dt=datetime.date.today()
        )
        event_data_raw = pandas.DataFrame(all_events)
        guid = self.guid
        event_data = (
            event_data_raw
            .query("pGuid == @guid")
        )
        event_data = (
            event_data
            .assign(
                **{
                    "begin": event_data["startDate"].apply(parse_pyicloud_datetime),
                    "end": event_data["endDate"].apply(parse_pyicloud_datetime)
                }
            )
        )

        return event_data