import warnings

from tuttle.model import Cycle, TimeUnit

warnings.warn(
    "wastebasket module, content will be moved to other modules",
    DeprecationWarning,
    stacklevel=2,
)

from typing import Callable, Optional

import datetime
import enum
from dataclasses import dataclass

from flet import View

from tuttle.dev import deprecated








@dataclass
class RouteView:
    """A utility class that defines a route view"""

    view: View
    keep_back_stack: bool
    on_window_resized: Callable
