import datetime

from ..core.abstractions import SQLModelDataSourceMixin, Intent
from ..core.intent_result import IntentResult
from ...model import Task

from .generator import generate_tasks


class TasksIntent(SQLModelDataSourceMixin, Intent):
    """Tasks CRUD with generator-driven refresh."""

    def __init__(self):
        SQLModelDataSourceMixin.__init__(self)

    def get_all(self) -> IntentResult:
        """Refresh tasks from business state, then return all non-dismissed."""
        try:
            with self.create_session() as session:
                generate_tasks(session)
            with self.create_session() as session:
                from sqlmodel import select

                tasks = session.exec(
                    select(Task).where(Task.status.in_(["pending", "done"]))  # type: ignore[union-attr]
                ).all()
                return IntentResult(was_intent_successful=True, data=tasks)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to load tasks.",
                log_message=f"TasksIntent.get_all: {e}",
                exception=e,
            )

    def mark_done(self, id: int) -> IntentResult:
        """Mark a task as done."""
        try:
            with self.create_session() as session:
                task = session.get(Task, id)
                if not task:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg="Task not found.",
                    )
                task.status = "done"
                session.add(task)
                session.commit()
                return IntentResult(was_intent_successful=True, data=task)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to mark task done.",
                log_message=f"TasksIntent.mark_done({id}): {e}",
                exception=e,
            )

    def dismiss(self, id: int) -> IntentResult:
        """Dismiss a task (hide without completing)."""
        try:
            with self.create_session() as session:
                task = session.get(Task, id)
                if not task:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg="Task not found.",
                    )
                task.status = "dismissed"
                session.add(task)
                session.commit()
                return IntentResult(was_intent_successful=True, data=task)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to dismiss task.",
                log_message=f"TasksIntent.dismiss({id}): {e}",
                exception=e,
            )

    def reopen(self, id: int) -> IntentResult:
        """Reopen a completed or dismissed task."""
        try:
            with self.create_session() as session:
                task = session.get(Task, id)
                if not task:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg="Task not found.",
                    )
                task.status = "pending"
                session.add(task)
                session.commit()
                return IntentResult(was_intent_successful=True, data=task)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to reopen task.",
                log_message=f"TasksIntent.reopen({id}): {e}",
                exception=e,
            )
