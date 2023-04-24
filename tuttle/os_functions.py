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
    try:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if platform.system() == "Darwin":
            subprocess.check_call(["qlmanage", "-p", file_path])
        elif platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Linux":
            subprocess.check_call(["xdg-open", file_path])
        else:
            raise RuntimeError("Sorry, your platform is not supported.")
    except subprocess.CalledProcessError as err:
        raise RuntimeError(
            f"Error occurred while opening the PDF file. Return code: {err.returncode}. Error: {err.output}"
        )


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
