from typing import Optional, List

from pathlib import Path
import webbrowser
import urllib.parse


def compose_email(
    to: str,
    subject: str,
    body: str,
    attachment_paths: Optional[List[Path]] = None,
):
    """Compose an email with the default email client."""
    url = "mailto:{}?subject={}&body={}".format(
        to,
        subject,
        body,
    )
    webbrowser.open(url)
