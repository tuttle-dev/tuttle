"""Data-access layer for the Salary feature."""

from typing import List

import sqlmodel

from ..core.abstractions import SQLModelDataSourceMixin
from ..core.intent_result import IntentResult
from ...model import RecurringExpense


class SalaryDataSource(SQLModelDataSourceMixin):
    """CRUD operations for RecurringExpense records."""

    def __init__(self):
        super().__init__()

    def get_all_expenses(self) -> IntentResult[List[RecurringExpense]]:
        try:
            expenses = self.query(RecurringExpense)
            return IntentResult(was_intent_successful=True, data=expenses)
        except Exception as ex:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load recurring expenses: {ex}",
                log_message=f"SalaryDataSource.get_all_expenses: {ex}",
                exception=ex,
            )

    def save_expense(self, expense: RecurringExpense) -> IntentResult[RecurringExpense]:
        try:
            with self.create_session() as session:
                session.add(expense)
                session.commit()
                session.refresh(expense)
            return IntentResult(was_intent_successful=True, data=expense)
        except Exception as ex:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to save recurring expense: {ex}",
                log_message=f"SalaryDataSource.save_expense: {ex}",
                exception=ex,
            )

    def delete_expense_by_id(self, expense_id: int) -> IntentResult:
        try:
            with self.create_session() as session:
                expense = session.exec(
                    sqlmodel.select(RecurringExpense).where(
                        RecurringExpense.id == expense_id
                    )
                ).one_or_none()
                if expense is None:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg=f"Expense with id={expense_id} not found.",
                    )
                session.delete(expense)
                session.commit()
            return IntentResult(was_intent_successful=True)
        except Exception as ex:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to delete recurring expense: {ex}",
                log_message=f"SalaryDataSource.delete_expense_by_id: {ex}",
                exception=ex,
            )
