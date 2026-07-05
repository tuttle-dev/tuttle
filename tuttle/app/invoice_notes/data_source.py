from typing import List, Optional

from loguru import logger
import sqlmodel

from ..core.abstractions import SQLModelDataSourceMixin
from ..core.intent_result import IntentResult
from ...model import InvoiceNote


class InvoiceNotesDataSource(SQLModelDataSourceMixin):
    """DB access for saved invoice notes."""

    def __init__(self):
        super().__init__()

    def get_all(self) -> IntentResult[List[InvoiceNote]]:
        try:
            notes = self.query(InvoiceNote)
            return IntentResult(was_intent_successful=True, data=notes)
        except Exception as ex:
            logger.error(f"Failed to load invoice notes: {ex}")
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load saved notes: {ex}",
                exception=ex,
            )

    def find_by_text(self, text: str) -> Optional[InvoiceNote]:
        """Return an existing note with exactly matching text, or None."""
        with self.create_session() as session:
            return session.exec(
                sqlmodel.select(InvoiceNote).where(InvoiceNote.text == text)
            ).first()

    def save(self, note: InvoiceNote):
        self.store(note)

    def delete(self, note_id: int):
        self.delete_by_id(InvoiceNote, note_id)
