#!/usr/bin/env python3
"""
Fetch tuttle-dev/tuttle release download counts from GitHub API,
broken down by OS/platform, displayed as an ASCII table.

Usage:
    uv run scripts/release_downloads.py
    uv run scripts/release_downloads.py --repo owner/repo
    uv run scripts/release_downloads.py --totals-only
"""

import argparse
import json
import re
import subprocess
from collections import defaultdict

from rich import box
from rich.console import Console
from rich.table import Table

PLATFORMS = ["macOS", "Linux", "Windows"]
# Skip update-check manifests (.yml), binary delta patches, and build metadata
# .yml = Electron updater pings (not actual downloads); .blockmap = delta patches
SKIP_PATTERNS = re.compile(r"\.blockmap$|\.yml$")
console = Console()


def classify(name: str) -> str | None:
    """Return platform label for an asset filename, or None to skip."""
    if SKIP_PATTERNS.search(name):
        return None
    n = name.lower()
    if ".dmg" in n or "macos" in n or "-mac" in n:
        return "macOS"
    if any(k in n for k in (".appimage", ".deb", ".rpm", "linux")):
        return "Linux"
    if any(k in n for k in (".exe", "setup", "windows", "win")):
        return "Windows"
    return None


def fetch_releases(repo: str) -> list[dict]:
    result = subprocess.run(
        ["gh", "api", "--paginate", f"repos/{repo}/releases"],
        capture_output=True,
        text=True,
        check=True,
    )
    # gh --paginate may return multiple JSON arrays; merge them
    raw = result.stdout.strip()
    if raw.startswith("[["):
        pages = json.loads(f"[{raw}]")
        releases = [r for page in pages for r in page]
    else:
        releases = json.loads(raw)
    return releases


def build_rows(releases: list[dict]) -> list[dict]:
    rows = []
    for rel in releases:
        counts: dict[str, int] = defaultdict(int)
        for asset in rel.get("assets", []):
            platform = classify(asset["name"])
            if platform:
                counts[platform] += asset["download_count"]
        rows.append(
            {
                "tag": rel["tag_name"],
                "date": rel["published_at"][:10],
                **{p: counts[p] for p in PLATFORMS},
                "total": sum(counts[p] for p in PLATFORMS),
            }
        )
    return rows


PLATFORM_COLORS = {"macOS": "cyan", "Linux": "yellow", "Windows": "blue"}


def _fmt(n: int) -> str:
    return "[dim]-[/dim]" if n == 0 else str(n)


def print_table(rows: list[dict], totals_only: bool = False) -> None:
    totals = {p: sum(r[p] for r in rows) for p in PLATFORMS}
    totals["total"] = sum(totals[p] for p in PLATFORMS)

    if totals_only:
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold")
        for p in PLATFORMS:
            table.add_column(p, justify="right", style=PLATFORM_COLORS[p])
        table.add_column("Total", justify="right", style="bold green")
        table.add_row(*[str(totals[p]) for p in PLATFORMS], str(totals["total"]))
        console.print(table)
        return

    table = Table(
        title="[bold]Tuttle — Release Downloads[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold",
        show_footer=True,
    )
    table.add_column("Release", style="bold white", footer="TOTAL")
    table.add_column("Date", style="dim", footer="")
    for p in PLATFORMS:
        table.add_column(
            p,
            justify="right",
            style=PLATFORM_COLORS[p],
            footer=f"[bold]{totals[p]}[/bold]",
        )
    table.add_column(
        "Total",
        justify="right",
        style="bold green",
        footer=f"[bold green]{totals['total']}[/bold green]",
    )

    for r in rows:
        table.add_row(
            r["tag"],
            r["date"],
            *[_fmt(r[p]) for p in PLATFORMS],
            _fmt(r["total"]).replace("[dim]-[/dim]", "[dim]-[/dim]"),
        )

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub release download stats by platform")
    parser.add_argument("--repo", default="tuttle-dev/tuttle", help="GitHub repo (owner/name)")
    parser.add_argument("--totals-only", action="store_true", help="Print only the summary row")
    args = parser.parse_args()

    releases = fetch_releases(args.repo)
    rows = build_rows(releases)
    print_table(rows, totals_only=args.totals_only)


if __name__ == "__main__":
    main()
