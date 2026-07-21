"""Build the Tuttle Electron app as a self-contained desktop bundle.

Phase 1: PyInstaller bundles tuttle/rpc_server.py into a standalone
         directory (dist/tuttle-rpc/) containing the CPython interpreter,
         the full tuttle package, all dependencies, and data files.

Phase 2: Vite builds the renderer, then electron-builder packages
         everything into a platform-native app (.app / .exe / AppImage),
         embedding the PyInstaller output as an extra resource.

Usage:
    uv run python scripts/pack_electron.py          # build for current platform
    uv run python scripts/pack_electron.py --skip-python   # skip PyInstaller, rebuild Electron only
"""

import subprocess
import sys
from pathlib import Path

import typer
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parent.parent
ELECTRON_DIR = REPO_ROOT / "ui"
SPEC_FILE = REPO_ROOT / "tuttle-rpc.spec"


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True):
    """Run a subprocess, streaming output to the terminal."""
    logger.info(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or REPO_ROOT)
    if check and result.returncode != 0:
        logger.error(f"Command failed with exit code {result.returncode}")
        raise typer.Exit(code=1)
    return result


def build_python_core():
    """Run PyInstaller to produce dist/tuttle-rpc/."""
    logger.info("Phase 1: Building Python core with PyInstaller")

    if not SPEC_FILE.exists():
        logger.error(f"PyInstaller spec not found: {SPEC_FILE}")
        raise typer.Exit(code=1)

    _run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(SPEC_FILE),
        ]
    )

    dist = REPO_ROOT / "dist" / "tuttle-rpc"
    if not dist.exists():
        logger.error(f"PyInstaller output not found at {dist}")
        raise typer.Exit(code=1)

    exe_name = "tuttle-rpc.exe" if sys.platform.startswith("win") else "tuttle-rpc"
    exe = dist / exe_name
    if not exe.exists():
        logger.error(f"Executable not found: {exe}")
        raise typer.Exit(code=1)

    logger.info(f"Python core ready at {dist}")

    # Fail fast if the frozen binary is missing any RPC domain.
    logger.info("Smoke-testing core: verifying every RPC domain is bundled")
    _run([sys.executable, str(REPO_ROOT / "scripts" / "smoke_core.py")])


def build_electron():
    """Run Vite build + electron-builder."""
    logger.info("Phase 2: Building Electron app")

    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"

    _run([npm, "ci"], cwd=ELECTRON_DIR)
    _run([npm, "run", "build"], cwd=ELECTRON_DIR)
    _run([npm, "run", "dist"], cwd=ELECTRON_DIR)

    release_dir = ELECTRON_DIR / "release"
    logger.info(f"Electron build output in {release_dir}")

    if sys.platform.startswith("darwin"):
        apps = list(release_dir.rglob("*.app"))
        if apps:
            logger.info(f"macOS app bundle: {apps[0]}")
    elif sys.platform.startswith("win"):
        exes = list(release_dir.rglob("*.exe"))
        if exes:
            logger.info(f"Windows installer: {exes[0]}")
    else:
        appimages = list(release_dir.rglob("*.AppImage"))
        if appimages:
            logger.info(f"Linux AppImage: {appimages[0]}")


def main(
    skip_python: bool = typer.Option(False, "--skip-python", help="Skip PyInstaller build, only rebuild Electron"),
):
    if not skip_python:
        build_python_core()
    else:
        logger.info("Skipping Python core build (--skip-python)")
        dist = REPO_ROOT / "dist" / "tuttle-rpc"
        if not dist.exists():
            logger.warning(f"No existing core build at {dist} -- electron-builder will fail")

    build_electron()
    logger.info("Build complete!")


if __name__ == "__main__":
    typer.run(main)
