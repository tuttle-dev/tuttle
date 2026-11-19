"""An event without a title is imported untagged, instead of failing the whole calendar."""

from tuttle.calendar import ICSCalendar

ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Tuttle//Test//EN
BEGIN:VEVENT
UID:titled@tuttle
DTSTART:20260601T090000Z
DTEND:20260601T110000Z
SUMMARY:Boiler service #heating
END:VEVENT
BEGIN:VEVENT
UID:untitled@tuttle
DTSTART:20260602T090000Z
DTEND:20260602T100000Z
END:VEVENT
END:VCALENDAR
"""


def test_an_untitled_event_is_imported_without_a_tag():
    data = ICSCalendar(name="Work", content=ICS).to_data()

    assert len(data) == 2
    assert sorted(data["tag"]) == ["", "#heating"]
    assert data.loc[data["tag"] == "", "duration"].iloc[0].total_seconds() == 3600
