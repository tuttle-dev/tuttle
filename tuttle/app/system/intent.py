"""System diagnostics exposed to the UI."""

from ..core.intent_result import IntentResult
from .log_sink import get_recent, clear


class SystemIntent:
    def get_logs(self, limit: int = 100, level: str = None) -> IntentResult:
        """Return recent backend log entries."""
        entries = get_recent(limit=limit, level=level)
        return IntentResult(was_intent_successful=True, data=entries)

    def clear_logs(self) -> IntentResult:
        """Clear the in-memory log buffer."""
        clear()
        return IntentResult(was_intent_successful=True, data=None)
