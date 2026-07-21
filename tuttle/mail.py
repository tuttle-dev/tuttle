import platform
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path
from typing import List, Optional

from loguru import logger


def compose_email(
    to: str,
    subject: str,
    body: str,
    attachment_paths: Optional[List[Path]] = None,
):
    """Open a new email draft in the default mail client with attachments.

    Platform strategies (when attachments are provided):
      - macOS:   AppleScript → Mail.app
      - Linux:   xdg-email --attach
      - Windows: Outlook COM via PowerShell, falls back to mailto: + open folder
    Without attachments, all platforms use a plain mailto: URL.
    """
    files = attachment_paths or []
    system = platform.system()

    if files:
        if system == "Darwin":
            _compose_macos(to, subject, body, files)
            return
        if system == "Linux":
            _compose_linux(to, subject, body, files)
            return
        if system == "Windows":
            if _compose_windows(to, subject, body, files):
                return
            logger.warning("Outlook COM failed; falling back to mailto: and opening attachment folder")
            _open_folder_windows(files[0].parent)

    _compose_mailto(to, subject, body)


# ---------------------------------------------------------------------------
# mailto: fallback (all platforms, no attachments)
# ---------------------------------------------------------------------------


def _compose_mailto(to: str, subject: str, body: str):
    params = urllib.parse.urlencode({"subject": subject, "body": body}, quote_via=urllib.parse.quote)
    webbrowser.open(f"mailto:{urllib.parse.quote(to)}?{params}")


# ---------------------------------------------------------------------------
# macOS — AppleScript → Mail.app
# ---------------------------------------------------------------------------


def _compose_macos(to: str, subject: str, body: str, files: List[Path]):
    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    attach = "\n".join(
        f'        make new attachment with properties {{file name:POSIX file "{path}"}} at after the last paragraph'
        for path in files
    )
    script = f"""
tell application "Mail"
    set newMessage to make new outgoing message with properties ¬
        {{subject:"{_esc(subject)}", content:"{_esc(body)}" & return & return, visible:true}}
    tell newMessage
        make new to recipient at end of to recipients ¬
            with properties {{address:"{_esc(to)}"}}
{attach}
    end tell
    activate
end tell
"""
    subprocess.Popen(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ---------------------------------------------------------------------------
# Linux — xdg-email
# ---------------------------------------------------------------------------


def _compose_linux(to: str, subject: str, body: str, files: List[Path]):
    cmd = ["xdg-email", "--subject", subject, "--body", body]
    for path in files:
        cmd += ["--attach", str(path)]
    cmd.append(to)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------------------
# Windows — Outlook COM via PowerShell
# ---------------------------------------------------------------------------


def _compose_windows(to: str, subject: str, body: str, files: List[Path]) -> bool:
    """Returns True on success, False if Outlook COM is unavailable."""

    def _ps_escape(s: str) -> str:
        return s.replace("'", "''")

    attach_lines = "\n".join(f"$mail.Attachments.Add('{_ps_escape(str(path))}')" for path in files)
    ps_script = f"""\
$ol = New-Object -ComObject Outlook.Application
$mail = $ol.CreateItem(0)
$mail.To = '{_ps_escape(to)}'
$mail.Subject = '{_ps_escape(subject)}'
$mail.Body = '{_ps_escape(body)}'
{attach_lines}
$mail.Display()
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _open_folder_windows(folder: Path):
    subprocess.Popen(["explorer", str(folder)])
