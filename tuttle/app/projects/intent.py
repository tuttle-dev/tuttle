from typing import Optional

from ...model import Project
from ..clients.intent import ClientsIntent
from ..contracts.intent import ContractsIntent
from ..core.abstractions import CrudIntent
from ..core.intent_result import IntentResult


class ProjectsIntent(CrudIntent):
    """Handles intents related to the projects data UI."""

    entity_type = Project
    deletion_guards = [
        ("invoices", "invoices", lambda i: i.number or f"#{i.id}"),
        ("timesheets", "timesheets", lambda t: t.title),
    ]
    __save_skip__ = {"contract", "timesheets", "invoices"}

    def __init__(self):
        super().__init__()
        self._clients_intent = ClientsIntent()
        self._contracts_intent = ContractsIntent()

    # -- Cross-entity delegates ------------------------------------------------

    def get_all_clients_as_map(self):
        return self._clients_intent.get_all_as_map()

    def get_all_contracts_as_map(self):
        return self._contracts_intent.get_all_as_map()

    # -- Project-specific logic ------------------------------------------------

    def _validated_save(self, project: Project) -> IntentResult[Optional[Project]]:
        is_updating = project.id is not None
        result = self.save(project)
        if not result.was_intent_successful:
            if is_updating:
                old = self.get_by_id(project.id)
                result.data = old.data if old.was_intent_successful else None
            result.error_msg = self._describe_save_error(result.exception)
            result.log_message_if_any()
        return result

    @staticmethod
    def _describe_save_error(exc: Optional[Exception]) -> str:
        if exc is None:
            return "Failed to save the project."
        detail = str(getattr(exc, "orig", exc))
        if "UNIQUE" in detail or "duplicate" in detail.lower():
            if "title" in detail:
                return "A project with this title already exists."
            if "tag" in detail:
                return "A project with this tag already exists."
            return "A project with these details already exists."
        if "NOT NULL" in detail:
            return "A required field is missing."
        if "FOREIGN KEY" in detail or "foreign key" in detail:
            return "The selected contract is invalid."
        return "Failed to save the project."

    def toggle_completed(self, id: int) -> IntentResult:
        """Toggle is_completed and clear the stage override so the board re-derives position."""
        result = self.get_by_id(id)
        if not result.was_intent_successful or not result.data:
            return IntentResult(was_intent_successful=False, error_msg="Project not found")
        project: Project = result.data
        project.is_completed = not project.is_completed
        project.stage = "Completed" if project.is_completed else None
        return self._validated_save(project)

    def set_stage(self, id: int, stage: Optional[str]) -> IntentResult:
        """Set the explicit pipeline stage for a project.

        Passing stage=None (or an empty string) clears the override and lets
        the date-derived status take effect again.  Passing stage='Completed'
        also sets is_completed=True; any other value clears is_completed.
        """
        result = self.get_by_id(id)
        if not result.was_intent_successful or not result.data:
            return IntentResult(was_intent_successful=False, error_msg="Project not found")
        project: Project = result.data
        project.stage = stage or None
        if stage == "Completed":
            project.is_completed = True
        elif stage in ("Lead", "Offer", "Upcoming", "Active"):
            project.is_completed = False
        return self._validated_save(project)
