"""Data visualization."""

import altair

from pandera.typing import DataFrame

from .dev import deprecated

# ALTAIR THEMES

# Vega color schemes: https://vega.github.io/vega/docs/schemes/
default_color_scheme = "category20"


def tuttle_dark():
    return {
        "config": {
            #'view': {'continuousHeight': 300, 'continuousWidth': 400},  # from the default theme
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
        plot_data = (
            planning_data.reset_index()
            .filter(["tag", "revenue"])
            .rename(columns={"tag": "project"})
        )
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
