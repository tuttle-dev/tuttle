"""Data-access layer for the Salary feature."""

from typing import List

import sqlmodel

from ...model import RecurringExpense
from ..core.abstractions import SQLModelDataSourceMixin
from ..core.intent_result import IntentResult, fails_with


class SalaryDataSource(SQLModelDataSourceMixin):
    """CRUD operations for RecurringExpense records."""

    def __init__(self):
        super().__init__()

    @fails_with("Failed to load recurring expenses", append_exception=True)
    def get_all_expenses(self) -> IntentResult[List[RecurringExpense]]:
        expenses = self.query(RecurringExpense)
        return IntentResult(was_intent_successful=True, data=expenses)

    @fails_with("Failed to save recurring expense", append_exception=True)
    def save_expense(self, expense: RecurringExpense) -> IntentResult[RecurringExpense]:
        with self.create_session() as session:
            session.add(expense)
            session.commit()
            session.refresh(expense)
        return IntentResult(was_intent_successful=True, data=expense)

    @fails_with("Failed to delete recurring expense", append_exception=True)
    def delete_expense_by_id(self, expense_id: int) -> IntentResult:
        with self.create_session() as session:
            expense = session.exec(sqlmodel.select(RecurringExpense).where(RecurringExpense.id == expense_id)).one_or_none()
            if expense is None:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg=f"Expense with id={expense_id} not found.",
                )
            session.delete(expense)
            session.commit()
        return IntentResult(was_intent_successful=True)
