from dataclasses import dataclass
from pathlib import Path


@dataclass
class Preferences:
    """Settings for the application."""

    home_dir: Path = None
    invoice_dir: Path = Path("Invoices")
