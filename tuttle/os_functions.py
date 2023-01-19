"""OS-level function"""
from typing import Optional, List
from pathlib import Path
import subprocess
import platform
import os


def open_application(app_name):
    """Open an application by name."""
    if platform.system() == "Darwin":
        subprocess.call(["open", "-a", app_name])
    elif platform.system() == "Windows":
        subprocess.call(["start", app_name], shell=True)
    elif platform.system() == "Linux":
        subprocess.call(["xdg-open", app_name])


def preview_pdf(file_path):
    """Preview a PDF file."""
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if platform.system() == "Darwin":
        os.system("qlmanage -p {}".format(file_path))
    elif platform.system() == "Windows":
        os.startfile(file_path)
    elif platform.system() == "Linux":
        os.system("xdg-open {}".format(file_path))
    else:
        print("Sorry, your platform is not supported.")


def open_folder(folder_path):
    """Open a folder."""
    if platform.system() == "Darwin":
        subprocess.call(["open", folder_path])
    elif platform.system() == "Windows":
        subprocess.call(["start", folder_path], shell=True)
    elif platform.system() == "Linux":
        subprocess.call(["xdg-open", folder_path])
    else:
        print("Sorry, your platform is not supported.")
