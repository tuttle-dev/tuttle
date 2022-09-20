from typing import Optional

import os
import sys
import subprocess
import typer
from pathlib import Path
from loguru import logger


added_files = [
    ("tuttle_tests/data", "./tuttle_tests/data"),
    ("templates", "./templates"),
]

added_data_options = [f"--add-data={src}:{dst}" for src, dst in added_files]


def build_macos(
    one_file: bool,
):
    pyinstaller_options = [
        "--noconfirm",
        "--windowed",
        "--clean",
    ]
    if one_file:
        pyinstaller_options += ["--onefile"]
    else:
        pyinstaller_options += ["--onedir"]

    options = pyinstaller_options + added_data_options

    logger.info(f"calling pyinstaller with options: {' '.join(options)}")
    subprocess.call(
        ["pyinstaller", "app/Tuttle.py"] + options,
        shell=False,
    )


def build_linux(
    one_file: bool,
):
    pyinstaller_options = [
        "--noconfirm",
        "--windowed",
        "--clean",
    ]

    if one_file:
        pyinstaller_options += ["--onefile"]
    else:
        pyinstaller_options += ["--onedir"]

    options = pyinstaller_options + added_data_options

    logger.info(f"calling pyinstaller with options: {' '.join(options)}")
    subprocess.call(
        ["pyinstaller", "app/Tuttle.py"] + options,
        shell=False,
    )


def build_windows(
    one_file: bool,
):
    pyinstaller_options = [
        "--noconfirm",
        "--windowed",
        "--clean",
        "--onefile",
    ]

    if one_file:
        pyinstaller_options += ["--onefile"]
    else:
        pyinstaller_options += ["--onedir"]

    # on Windows the separator is a semicolon
    added_data_options = [option.replace(":", ";") for option in added_data_options]

    options = pyinstaller_options + added_data_options

    logger.info(f"calling pyinstaller with options: {' '.join(options)}")
    subprocess.call(
        ["pyinstaller", "app/Tuttle.py"] + options,
        shell=False,
    )


def main(
    install_dir: Optional[Path] = typer.Option(
        None, "--install-dir", "-i", help="Where to install the app"
    ),
    one_file: bool = typer.Option(
        False, "--one-file", "-f", help="Build a single file executable"
    ),
):
    if install_dir:
        logger.info(f"removing app from {install_dir}")
        subprocess.call(["rm", "-rf", f"{install_dir}/Tuttle.app"], shell=False)

    # which operating system?
    if sys.platform.startswith("linux"):
        logger.info("building for Linux")
        build_linux(
            one_file=one_file,
        )
    elif sys.platform.startswith("darwin"):
        logger.info("building for macOS")
        build_macos(
            one_file=one_file,
        )
    elif sys.platform.startswith("win"):
        logger.info("building for Windows")
        build_windows(
            one_file=one_file,
        )
    else:
        raise RuntimeError("Unsupported operating system")

    if install_dir:
        logger.info(f"installing to {install_dir}")
        subprocess.call(
            ["cp", "-r", "dist/Tuttle.app", install_dir],
            shell=False,
        )


if __name__ == "__main__":
    typer.run(main)
