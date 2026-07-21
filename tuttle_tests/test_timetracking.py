"""Test timetracking module"""

import datetime
from decimal import Decimal

import pandas

from tuttle import timetracking
from tuttle.calendar import get_month_start_end
from tuttle.model import Address, Client, Contract, Project
from tuttle.time import Cycle, TimeUnit


def test_timetracking_import_toggl():
    """Test import of time tracking data from csv exported by Toggl."""
    data = timetracking.import_from_spreadsheet(
        path="tuttle_tests/data/test_time_tracking_toggl.csv",
        preset=timetracking.TogglPreset,
    )
    assert not data.empty

    pass


def test_calendar_to_data(demo_calendar_timetracking):
    time_tracking_data = demo_calendar_timetracking.to_data()
    assert not time_tracking_data.empty


def test_generate_timesheet_from_demo_calendar(
    demo_projects,
    demo_calendar_timetracking,
):
    for period in ["January 2022", "February 2022"]:
        (period_start, period_end) = get_month_start_end(period)
        for project in demo_projects:
            timesheet = timetracking.generate_timesheet(
                timetracking_data=demo_calendar_timetracking.to_data(),
                project=project,
                period_start=period_start,
                period_end=period_end,
                item_description=project.title,
            )
            assert (timesheet.empty) or (timesheet.total >= pandas.Timedelta("0 hours"))


def test_create_timesheet(
    demo_projects,
):
    # create synthetic time tracking data
    data = {
        "begin": ["01-01-2022 08:00:00", "01-02-2022 08:00:00"],
        "end": ["01-01-2022 12:00:00", "01-02-2022 12:00:00"],
        "title": ["Task 1", "Task 2"],
        "tag": ["#HeatingEngineering", "#HeatingEngineering"],
        "description": ["Work on task 1", "Work on task 2"],
        "all_day": [False, False],
    }
    timetracking_data = pandas.DataFrame(data)
    timetracking_data["begin"] = pandas.to_datetime(timetracking_data["begin"], format="%m-%d-%Y %H:%M:%S")
    timetracking_data["end"] = pandas.to_datetime(timetracking_data["end"], format="%m-%d-%Y %H:%M:%S")
    timetracking_data["duration"] = timetracking_data["end"] - timetracking_data["begin"]
    timetracking_data = timetracking_data.set_index("begin")

    assert timetracking_data["duration"].sum() == pandas.Timedelta("8 hours")

    project = demo_projects[0]

    # create a timesheet
    period_start = datetime.date(2022, 1, 1)
    period_end = datetime.date(2022, 12, 31)
    timesheet = timetracking.generate_timesheet(timetracking_data, project, period_start, period_end)

    # test timesheet properties
    assert timesheet.project.title == "Heating Engineering"
    assert timesheet.comment == ""
    assert timesheet.date == datetime.date.today()
    assert timesheet.total == datetime.timedelta(hours=8)
    assert not timesheet.empty
    # period dates must be date objects (not strings) for SQLite persistence
    assert isinstance(timesheet.period_start, datetime.date)
    assert isinstance(timesheet.period_end, datetime.date)
    assert timesheet.period_start == period_start
    assert timesheet.period_end == period_end


# ---------------------------------------------------------------------------
# Bug B / Bug C regression tests
# ---------------------------------------------------------------------------


def _make_project(tag: str, unit: TimeUnit, units_per_workday: int = 8) -> Project:
    client = Client(
        name="Acme",
        address=Address(
            street="Main",
            number="1",
            postal_code="00000",
            city="Nowhere",
            country="N/A",
        ),
    )
    contract = Contract(
        title="Test",
        client=client,
        signature_date=datetime.date(2022, 1, 1),
        start_date=datetime.date(2022, 1, 1),
        rate=Decimal("100"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        unit=unit,
        units_per_workday=units_per_workday,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    return Project(
        title=f"Project {tag}",
        description="",
        tag=tag,
        contract=contract,
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 12, 31),
    )


def test_generate_timesheet_handles_tz_boundary():
    """Bug C: event at month boundary in UTC must land in the local-time month.

    A calendar event at 2022-01-31 23:00 UTC is 2022-02-01 00:00 CET. With
    naive string-key slicing the event was silently dropped from February's
    timesheet; with date-based masking on the tz-aware index it correctly
    appears in February.
    """
    tag = "#TzProj"
    project = _make_project(tag, TimeUnit.hour)

    begin = pandas.to_datetime(["2022-01-31 23:00:00"], utc=True).tz_convert("CET")
    end = pandas.to_datetime(["2022-02-01 00:00:00"], utc=True).tz_convert("CET")
    df = pandas.DataFrame(
        {
            "end": end,
            "title": ["Late work"],
            "tag": [tag],
            "description": [""],
            "all_day": [False],
        },
        index=pandas.Index(begin, name="begin"),
    )
    df["duration"] = df["end"] - df.index

    timesheet = timetracking.generate_timesheet(
        timetracking_data=df,
        project=project,
        period_start=datetime.date(2022, 2, 1),
        period_end=datetime.date(2022, 2, 28),
    )

    assert timesheet.total == datetime.timedelta(hours=1)
    assert len(timesheet.items) == 1


def test_generate_timesheet_all_day_expansion_hour_unit():
    """Bug B (hour unit): all-day event expands to units_per_workday hours."""
    tag = "#AllDayHour"
    project = _make_project(tag, TimeUnit.hour, units_per_workday=8)

    df = pandas.DataFrame(
        {
            "begin": pandas.to_datetime(["2022-01-03 00:00:00"]),
            "end": pandas.to_datetime(["2022-01-04 00:00:00"]),
            "title": ["All-day work"],
            "tag": [tag],
            "description": [""],
            "all_day": [True],
        }
    )
    df["duration"] = df["end"] - df["begin"]
    df = df.set_index("begin")

    timesheet = timetracking.generate_timesheet(
        timetracking_data=df,
        project=project,
        period_start=datetime.date(2022, 1, 1),
        period_end=datetime.date(2022, 1, 31),
    )

    assert timesheet.total == datetime.timedelta(hours=8)


def test_generate_timesheet_all_day_expansion_day_unit():
    """Bug B (day unit): an all-day event still represents 8 hours of work, not 8 days.

    Previously the expansion was ``unit.to_timedelta() * units_per_workday``, which
    for unit=day, units_per_workday=8 yielded eight whole days per event.
    """
    tag = "#AllDayDay"
    project = _make_project(tag, TimeUnit.day, units_per_workday=8)

    df = pandas.DataFrame(
        {
            "begin": pandas.to_datetime(["2022-01-03 00:00:00"]),
            "end": pandas.to_datetime(["2022-01-04 00:00:00"]),
            "title": ["All-day work"],
            "tag": [tag],
            "description": [""],
            "all_day": [True],
        }
    )
    df["duration"] = df["end"] - df["begin"]
    df = df.set_index("begin")

    timesheet = timetracking.generate_timesheet(
        timetracking_data=df,
        project=project,
        period_start=datetime.date(2022, 1, 1),
        period_end=datetime.date(2022, 1, 31),
    )

    assert timesheet.total == datetime.timedelta(hours=8)


def test_generate_timesheet_preserves_per_event_descriptions():
    """item_description fallback must not overwrite per-event calendar descriptions."""
    tag = "#DescProj"
    project = _make_project(tag, TimeUnit.hour)

    df = pandas.DataFrame(
        {
            "begin": pandas.to_datetime(["2022-03-01 09:00:00", "2022-03-02 09:00:00"]),
            "end": pandas.to_datetime(["2022-03-01 11:00:00", "2022-03-02 11:00:00"]),
            "title": ["Meeting", "Deep work"],
            "tag": [tag, tag],
            "description": ["Notes from meeting", ""],
            "all_day": [False, False],
        }
    )
    df["duration"] = df["end"] - df["begin"]
    df = df.set_index("begin")

    timesheet = timetracking.generate_timesheet(
        timetracking_data=df,
        project=project,
        period_start=datetime.date(2022, 3, 1),
        period_end=datetime.date(2022, 3, 31),
        item_description="Fallback description",
    )

    items = {item.title: item for item in timesheet.items}
    # Row with an existing description must keep it.
    assert items["Meeting"].description == "Notes from meeting"
    # Row with no description gets the fallback.
    assert items["Deep work"].description == "Fallback description"


# ---------------------------------------------------------------------------
# Aggregation regression tests — tz-aware data (real ICS imports)
# ---------------------------------------------------------------------------


def test_df_to_records_with_tz_aware_data():
    """Regression: df_to_records must not crash on tz-aware timestamps.

    ICS calendar imports produce CET-localized Timestamps. A naive
    datetime.now() comparison causes TypeError.
    """
    from tuttle.app.timetracking.aggregation import df_to_records

    begin = pandas.to_datetime(["2026-07-01 09:00:00", "2026-12-01 09:00:00"], utc=True).tz_convert("CET")
    end = pandas.to_datetime(["2026-07-01 11:00:00", "2026-12-01 11:00:00"], utc=True).tz_convert("CET")

    df = pandas.DataFrame(
        {
            "end": end,
            "title": ["Past event", "Future event"],
            "tag": ["#proj", "#proj"],
            "description": ["", ""],
            "all_day": [False, False],
        },
        index=pandas.Index(begin, name="begin"),
    )
    df["duration"] = df["end"] - df.index

    records = df_to_records(df)
    assert len(records) == 2
    assert records[0]["is_future"] is False
    assert records[1]["is_future"] is True


def test_build_calendar_data_with_tz_aware_data():
    """Regression: build_calendar_data must handle tz-aware DataFrames."""
    from tuttle.app.timetracking.aggregation import build_calendar_data

    begin = pandas.to_datetime(["2026-07-03 09:00:00", "2026-07-04 14:00:00"], utc=True).tz_convert("CET")
    end = pandas.to_datetime(["2026-07-03 11:00:00", "2026-07-04 16:00:00"], utc=True).tz_convert("CET")

    df = pandas.DataFrame(
        {
            "end": end,
            "title": ["Task A", "Task B"],
            "tag": ["#alpha", "#beta"],
            "description": ["", ""],
            "all_day": [False, False],
        },
        index=pandas.Index(begin, name="begin"),
    )
    df["duration"] = df["end"] - df.index

    result = build_calendar_data(df, 2026, 7)
    assert result["year"] == 2026
    assert result["month"] == 7
    assert result["summary"]["total_events"] == 2
    assert result["summary"]["total_hours"] > 0
    assert len(result["events"]) == 2
