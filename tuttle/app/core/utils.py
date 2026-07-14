"""Utility functions shared across the application."""

import base64

from .formatting import fmt_currency  # noqa: F401 — re-export


def truncate_str(txt: str, max_chars: int = 25) -> str:
    if not txt:
        return ""
    if len(txt) <= max_chars:
        return txt
    else:
        return f"{txt[0:max_chars]}..."


def image_to_base64(image_path):
    """Converts an image to a base64-encoded string."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string
