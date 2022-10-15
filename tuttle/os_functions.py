"""OS-level function"""
from typing import Optional
import subprocess
import platform
from pathlib import Path


def open_application(app_name):
    """Open an application by name."""
    if platform.system() == "Darwin":
        subprocess.call(["open", "-a", app_name])
    elif platform.system() == "Windows":
        subprocess.call(["start", app_name], shell=True)
    elif platform.system() == "Linux":
        subprocess.call(["xdg-open", app_name])


def run_applescript(script):
    """Run an AppleScript."""
    subprocess.call(["osascript", "-e", script])


def compose_email(
    recipient: str,
    subject: str,
    body: str,
    attachment_path: Optional[Path],
):
    """Compose an email in the default email application."""
    if platform.system() == "Darwin":
        script_set_attachment = f"""
        set theAttachmentPath to "{attachment_path}"
        set theAttachmentFile to (theAttachmentPath as POSIX file)
        """

        script_set_vars = f"""
        set theSubject to "{subject}"
        set theBody to "{body}"
        set theAddress to "{recipient}"
        """

        script_compose_email = """
        tell application "Mail" to activate
        tell application "Mail"
            set theNewMessage to make new outgoing message with properties {subject:theSubject, content:theBody & return & return, visible:true}
            tell theNewMessage
                set visibile to true
                #set sender to theSender
                make new recipient at end of to recipients with properties {address:theAddress}
                try
                    make new attachment with properties {file name:theAttachmentFile} at after the last word of the last paragraph
                    set message_attachment to 0
                on error errmess -- oops
                    log errmess -- log the error
                    set message_attachment to 1
                end try
            end tell
        end tell
        """

        script = script_set_attachment + script_set_vars + script_compose_email
        run_applescript(script)
    else:
        raise ValueError("Unsupported OS")
