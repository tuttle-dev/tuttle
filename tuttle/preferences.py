from dataclasses import dataclass
from pathlib import Path

from tuttle.dev import deprecated


@deprecated("Use model class Settings instead")
@dataclass
class Preferences:
    """Settings for the application."""

    home_dir: Path = None
    invoice_dir: Path = Path("Invoices")
    # TODO: time tracking preference
