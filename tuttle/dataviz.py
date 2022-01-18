"""Data visualization."""

import altair

from pandera.typing import DataFrame


def enable_dark_theme():
    """Enable the built-in Altair dark theme"""
    altair.renderers.set_embed_options(theme="dark")
