"""Data visualization."""

import altair

from pandera.typing import DataFrame

from .dev import deprecated

# ALTAIR THEMES

# Vega color schemes: https://vega.github.io/vega/docs/schemes/
default_color_scheme = "category20c"


def tuttle_dark():
    return {
        "config": {
            #'view': {'continuousHeight': 300, 'continuousWidth': 400},  # from the default theme
            "range": {"category": {"scheme": "category20c"}}
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


@deprecated("Use dataviz.enable_theme('default_dark') instead")
def enable_dark_theme():
    """Enable the built-in Altair dark theme"""
    altair.renderers.set_embed_options(theme="dark")
