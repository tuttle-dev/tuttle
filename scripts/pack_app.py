from typing import Optional

import sys
from pathlib import Path
import typer
from loguru import logger
import subprocess

import tuttle

app_path = "app/app.py"
app_name = "Tuttle"
icon_path = "app/assets/icon/macos/AppIcon.icns"

# files to be added to the app bundle
added_files = [
    ("templates", "./templates"),
    ("tuttle_tests/data", "./tuttle_tests/data"),
]

# options to be passed to flet pack
pack_options = [
    ("--name", app_name),
    ("--icon", icon_path),
    ("--product-name", app_name),
    ("--product-version", tuttle.__version__),
    ("--copyright", "© 2021-2023 Tuttle developers. Licsened under the GNU GPL v3.0."),
]

if sys.platform.startswith("win"):
    delimiter = ";"
else:
    delimiter = ":"

added_data_options = []
for src, dst in added_files:
    added_data_options += ["--add-data", f"{src}{delimiter}{dst}"]
pack_options_unpacked = [item for pair in pack_options for item in pair]


def main(
    install_dir: Optional[Path] = typer.Option(
        None, "--install-dir", "-i", help="Where to install the app"
    ),
):
    if install_dir:
        logger.info(f"removing app from {install_dir}")
        subprocess.call(["rm", "-rf", f"{install_dir}/Tuttle.app"], shell=False)

    logger.info("building app")
    pack_command = (
        ["flet", "pack", app_path] + added_data_options + pack_options_unpacked
    )
    logger.info(f"calling flet with command: {' '.join(pack_command)}")
    print(pack_command)
    subprocess.call(
        pack_command,
        shell=False,
    )


if __name__ == "__main__":
    typer.run(main)
