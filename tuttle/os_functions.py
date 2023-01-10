"""OS-level function"""
from typing import Optional, List
import subprocess
import platform


def open_application(app_name):
    """Open an application by name."""
    if platform.system() == "Darwin":
        subprocess.call(["open", "-a", app_name])
    elif platform.system() == "Windows":
        subprocess.call(["start", app_name], shell=True)
    elif platform.system() == "Linux":
        subprocess.call(["xdg-open", app_name])
