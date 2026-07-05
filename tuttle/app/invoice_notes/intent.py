from typing import List

from loguru import logger

from ..core.abstractions import Intent
from ..core.intent_result import IntentResult
from ...model import InvoiceNote

from .data_source import InvoiceNotesDataSource


class InvoiceNotesIntent(Intent):
    """CRUD for saved invoice notes."""

    def __init__(self):
        self._ds = InvoiceNotesDataSource()

    def get_all(self) -> IntentResult[List[InvoiceNote]]:
        return self._ds.get_all()

    def create(self, text: str) -> IntentResult[InvoiceNote]:
        """Create a new saved note, deduplicating by text."""
        text = text.strip()
        if not text:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Note text must not be empty.",
            )
        existing = self._ds.find_by_text(text)
        if existing:
            return IntentResult(was_intent_successful=True, data=existing)
        try:
            note = InvoiceNote(text=text)
            self._ds.save(note)
            return IntentResult(was_intent_successful=True, data=note)
        except Exception as ex:
            logger.error(f"Failed to create invoice note: {ex}")
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to save note: {ex}",
            )

    def delete(self, id: int) -> IntentResult[None]:
        try:
            self._ds.delete(id)
            return IntentResult(was_intent_successful=True)
        except Exception as ex:
            logger.error(f"Failed to delete invoice note {id}: {ex}")
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to delete note: {ex}",
            )
