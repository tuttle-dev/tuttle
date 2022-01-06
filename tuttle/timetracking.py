from dataclasses import dataclass

import pandas

from tuttle.calendar import Calendar


@dataclass
class Timesheet:
    """dataframe-based timesheet"""

    table: pandas.DataFrame
    period: str
    client: str
    comment: str = None

    def total(self):
        total_hours = self.table["hours"].sum()
        return total_hours


def generate_timesheet(
    cal: Calendar,
    period: str,
    client: str,
    comment: str,
) -> Timesheet:
    # convert cal to data
    cal_data = cal.to_data()

    ts_table = (
        cal_data.loc[period]
        .query(f"title == '{client}'")
        .filter(["duration"])
        .sort_index()
    )

    ts_table = ts_table.groupby(by=ts_table.index.date).sum()
    ts_table["hours"] = (
        ts_table["duration"]
        .dt.components["hours"]
        .add((ts_table["duration"].dt.components["days"] * 24))
    )
    ts_table = (
        ts_table.assign(**{"comment": comment})
        # .reset_index()
        .filter(["hours", "comment"])  #
        .reset_index()
        .rename(columns={"index": "date"})
    )

    ts_table["date"] = pandas.to_datetime(ts_table["date"])
    ts_table = ts_table.set_index("date")

    ts = Timesheet(period=period, client=client, comment=comment, table=ts_table)

    return ts


def export_timesheet(
    timesheet: Timesheet,
    path: str,
):
    table = timesheet.table
    table = table.reset_index()
    table["date"] = table["date"].dt.strftime("%Y/%m/%d")
    table.loc["Total", :] = ("Total", table["hours"].sum(), "")
    table.to_excel(path, index=False)
