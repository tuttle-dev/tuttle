from typing import Optional, List

from pathlib import Path
import webbrowser
import urllib.parse


def compose_email(
    recipient: str,
    subject: str,
    body: str,
    attachment_paths: Optional[List[Path]] = None,
):
    """Compose an email with the default email client."""
    attachments = ""
    if attachment_paths:
        for i, attachment_path in enumerate(attachment_paths):
            attachments += "&attachment{}={}".format(i + 1, str(attachment_path))
    url = "mailto:{}?subject={}&body={}{}".format(
        recipient,
        subject,
        urllib.parse.quote(body),
        attachments,
    )
    webbrowser.open(url)
