import pandas

from calendar import Calendar
from model import Timesheet


def generate_timesheet(
    cal: Calendar, period: str, client: str, comment: str
) -> pandas.DataFrame:
    # convert cal to data
    cal_data = cal.to_data()

    timesheeet = (
        cal_data.loc[period]
        .query(f"name == '{client}'")
        .filter(["duration"])
        .sort_index()
    )

    timesheeet = timesheeet.groupby(by=timesheeet.index.date).sum()
    timesheeet["hours"] = (
        timesheeet["duration"]
        .dt.components["hours"]
        .add((timesheeet["duration"].dt.components["days"] * 24))
    )
    timesheeet = (
        timesheeet.assign(**{"comment": comment})
        # .reset_index()
        .filter(["hours", "comment"])  #
        .reset_index()
        .rename(columns={"index": "date"})
    )

    timesheeet["date"] = pandas.to_datetime(timesheeet["date"])
    timesheeet = timesheeet.set_index("date")

    return timesheeet


def export_timesheet(timesheet: Timesheet, path: str):
    table = timesheet.table.reset_index()
    table["date"] = table["date"].dt.strftime("%Y/%m/%d")
    table.loc["Total", :] = ("Total", timesheet["hours"].sum(), "")
    table.to_excel(path, index=False)
