"""OS-level function"""

import base64
import os
import platform
import subprocess
from pathlib import Path
from typing import List, Optional

import pymupdf


def open_application(app_name):
    """Open an application by name."""
    if platform.system() == "Darwin":
        subprocess.call(["open", "-a", app_name])
    elif platform.system() == "Windows":
        subprocess.call(["start", app_name], shell=True)
    elif platform.system() == "Linux":
        subprocess.call(["xdg-open", app_name])


_ql_process: Optional[subprocess.Popen] = None


def preview_pdf(file_path):
    """Preview a PDF file using the system Quick Look (macOS) or default viewer.

    Non-blocking.  On macOS only one Quick Look window is kept alive at a time;
    repeated calls replace the previous preview.
    """
    global _ql_process
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    system = platform.system()
    if system == "Darwin":
        # Tear down a previous Quick Look window so we never stack them up.
        if _ql_process is not None and _ql_process.poll() is None:
            _ql_process.terminate()
            try:
                _ql_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                _ql_process.kill()

        _ql_process = subprocess.Popen(
            ["qlmanage", "-p", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Best-effort: bring the Quick Look window to the foreground.
        subprocess.Popen(
            [
                "osascript",
                "-e",
                'tell application "System Events" to set frontmost of every process whose name is "qlmanage" to true',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif system == "Windows":
        os.startfile(str(path))
    elif system == "Linux":
        subprocess.Popen(
            ["xdg-open", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        raise RuntimeError("Sorry, your platform is not supported.")


def render_pdf_pages(file_path, dpi: int = 150) -> List[str]:
    """Render each page of a PDF to a base64-encoded PNG string.

    Returns a list with one base64 string per page.
    Raises FileNotFoundError when the path does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    zoom = dpi / 72  # 72 is the PDF base resolution
    matrix = pymupdf.Matrix(zoom, zoom)
    pages: List[str] = []
    with pymupdf.open(str(path)) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix)
            pages.append(base64.b64encode(pix.tobytes("png")).decode("ascii"))
    return pages


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
