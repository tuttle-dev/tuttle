import os
import sys
import subprocess

from loguru import logger

added_files = [
    ("tuttle_tests/data", "demo_data"),
    ("templates", "templates"),
]

added_data_options = [f"--add-data={src}:{dst}" for src, dst in added_files]


def build_macos():
    pyinstaller_options = [
        "--noconfirm",
        "--windowed",
        "--clean",
        "--onefile",
        # "--onedir",
    ]

    options = pyinstaller_options + added_data_options

    logger.info(f"calling pyinstaller with options: {' '.join(options)}")
    subprocess.call(
        ["pyinstaller", "app/Tuttle.py"] + options,
        shell=False,
    )


def build_linux():
    pyinstaller_options = [
        "--noconfirm",
        "--windowed",
        "--clean",
        "--onefile",
        # "--onedir",
    ]

    options = pyinstaller_options + added_data_options

    logger.info(f"calling pyinstaller with options: {' '.join(options)}")
    subprocess.call(
        ["pyinstaller", "app/Tuttle.py"] + options,
        shell=False,
    )


def build_windows():
    pyinstaller_options = [
        "--noconfirm",
        "--windowed",
        "--clean",
        "--onefile",
        # "--onedir",
    ]

    options = pyinstaller_options + added_data_options

    logger.info(f"calling pyinstaller with options: {' '.join(options)}")
    subprocess.call(
        ["pyinstaller", "app/Tuttle.py"] + options,
        shell=False,
    )


def main():
    # which operating system?
    if sys.platform.startswith("linux"):
        logger.info("building for Linux")
        build_linux()
    elif sys.platform.startswith("darwin"):
        logger.info("building for macOS")
        build_macos()
    elif sys.platform.startswith("win"):
        logger.info("building for Windows")
        build_windows()
    else:
        raise RuntimeError("Unsupported operating system")


if __name__ == "__main__":
    main()

# os.system(
#     "pyinstaller app/Tuttle.py --onefile --noconsole --noconfirm --add-data 'tuttle_tests/data/TuttleDemo-TimeTracking.ics:.'"
# )
