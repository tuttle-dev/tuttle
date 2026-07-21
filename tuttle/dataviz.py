"""Data visualization."""

from typing import List, Optional

import altair
import pandas

# from pandera.typing import DataFrame
from pandas import DataFrame

# ALTAIR THEMES

# Vega color schemes: https://vega.github.io/vega/docs/schemes/
default_color_scheme = "category20"


def tuttle_dark():
    return {
        "config": {
            # 'view': {'continuousHeight': 300, 'continuousWidth': 400},  # from the default theme
            "range": {"category": {"scheme": "category20"}}
        }
    }


def enable_theme(theme_name="tuttle_dark"):
    """Enable one of the available custom Altair theme."""
    if theme_name == "tuttle_dark":
        altair.themes.register("tuttle_dark", tuttle_dark)
        altair.themes.enable("tuttle_dark")
        altair.renderers.set_embed_options(theme="dark")
    elif theme_name == "default_dark":
        altair.renderers.set_embed_options(theme="dark")
    else:
        raise ValueError("unknown theme: {theme_name}")


def plot_eval_time_planning(
    planning_data,
    by,
):
    if by == "project":
        plot_data = planning_data.reset_index().filter(["tag", "revenue"]).rename(columns={"tag": "project"})
        plot = (
            altair.Chart(plot_data)
            .mark_bar()
            .encode(
                y="project:N",
                x="revenue:Q",
            )
            .properties(width=600)
        )
    elif by == ("month", "project"):
        plot_data = (
            planning_data.reset_index()
            .filter(["tag", "begin", "revenue"])
            .rename(columns={"tag": "project", "begin": "month_end"})
        )
        plot = (
            altair.Chart(plot_data)
            .mark_bar()
            .encode(
                y=altair.Y(
                    "yearmonth(month_end):O",
                    axis=altair.Axis(title="month"),
                ),
                x=altair.X(
                    "revenue:Q",
                ),
                color="project:N",
            )
            .properties(width=600)
        )
    else:
        raise ValueError(f"unknown mode {by}")
    return plot


def plot_revenue_curve(
    revenue_data: DataFrame,
    goals: Optional[List[dict]] = None,
) -> altair.LayerChart:
    """Plot historical + forecast revenue curve with optional goal markers.

    Args:
        revenue_data: DataFrame with columns: month, revenue, is_forecast, cumulative_revenue.
        goals: Optional list of dicts with keys: title, target_amount, target_date.

    Returns:
        An Altair LayerChart.
    """
    revenue_data = revenue_data.copy()
    revenue_data["month"] = pandas.to_datetime(revenue_data["month"])
    revenue_data["type"] = revenue_data["is_forecast"].map({True: "Forecast", False: "Actual"})

    # Monthly revenue bars
    bars = (
        altair.Chart(revenue_data)
        .mark_bar(opacity=0.7)
        .encode(
            x=altair.X("yearmonth(month):O", axis=altair.Axis(title="Month")),
            y=altair.Y("revenue:Q", axis=altair.Axis(title="Revenue (€)")),
            color=altair.Color(
                "type:N",
                scale=altair.Scale(
                    domain=["Actual", "Forecast"],
                    range=["#0A84FF", "#8E8E93"],
                ),
                legend=altair.Legend(title="Type"),
            ),
        )
        .properties(width=600, height=300)
    )

    # Cumulative revenue line
    line = (
        altair.Chart(revenue_data)
        .mark_line(strokeWidth=2, color="#30D158")
        .encode(
            x="yearmonth(month):O",
            y=altair.Y("cumulative_revenue:Q", axis=altair.Axis(title="")),
        )
    )

    layer = bars + line

    # Goal markers
    if goals:
        goal_df = DataFrame(goals)
        goal_df["target_date"] = pandas.to_datetime(goal_df["target_date"])
        goal_rules = (
            altair.Chart(goal_df)
            .mark_rule(strokeDash=[4, 4], color="#FFD60A", strokeWidth=2)
            .encode(
                y="target_amount:Q",
            )
        )
        goal_labels = (
            altair.Chart(goal_df)
            .mark_text(align="left", dx=5, dy=-5, color="#FFD60A", fontSize=11)
            .encode(
                y="target_amount:Q",
                text="title:N",
            )
        )
        layer = layer + goal_rules + goal_labels

    return layer


def plot_monthly_revenue_bars(
    monthly_data: list,
) -> altair.Chart:
    """Simple monthly revenue bar chart for the KPI overview.

    Args:
        monthly_data: List of dicts with keys: month, revenue.
    """
    df = DataFrame(monthly_data)
    df["revenue"] = df["revenue"].astype(float)

    chart = (
        altair.Chart(df)
        .mark_bar(color="#0A84FF")
        .encode(
            x=altair.X("month:O", axis=altair.Axis(title="Month", labelAngle=-45)),
            y=altair.Y("revenue:Q", axis=altair.Axis(title="Revenue (€)")),
        )
        .properties(width=600, height=250)
    )
    return chart


def chart_to_html(chart: altair.TopLevelMixin) -> str:
    """Render an Altair chart to a self-contained HTML string for embedding."""
    return chart.to_html()
