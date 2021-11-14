"""Calendar integration."""

import ics
import pyicloud
import getpass
import pandas

from pathlib import Path


class Calendar:
    """A calendar."""

    def __init__(
        self,
        path
    ):
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
        event_data["time"] = event_data["begin"]
        event_data = event_data.set_index("time")
        return event_data

            