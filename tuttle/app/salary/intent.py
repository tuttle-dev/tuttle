"""Business logic for the Salary feature."""

from ..core.abstractions import SQLModelDataSourceMixin, Intent
from ..core.intent_result import IntentResult

from ...model import Invoice, RecurringExpense, User
from ...tax import get_tax_system
from ...tax_reserves import compute_effective_salary

from .data_source import SalaryDataSource


class SalaryIntent(SQLModelDataSourceMixin, Intent):
    """Gathers and processes data for the Effective Salary view."""

    def __init__(self):
        SQLModelDataSourceMixin.__init__(self)
        self._data_source = SalaryDataSource()

    def _get_country(self) -> str:
        try:
            users = self.query(User)
            if users and users[0].operating_country:
                return users[0].operating_country
        except Exception:
            pass
        return "Germany"

    def _get_tax_currency(self, country: str) -> str:
        try:
            return get_tax_system(country).currency
        except NotImplementedError:
            return "EUR"

    def get_effective_salary(self) -> IntentResult:
        """Compute the effective salary range."""
        try:
            invoices = self.query(Invoice)
            expenses_result = self._data_source.get_all_expenses()
            expenses = (
                expenses_result.data if expenses_result.was_intent_successful else []
            )

            country = self._get_country()
            currency = self._get_tax_currency(country)

            salary = compute_effective_salary(
                invoices=invoices,
                expenses=expenses,
                country=country,
                currency=currency,
            )
            return IntentResult(
                was_intent_successful=True,
                data={"salary": salary, "currency": currency},
            )
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to compute effective salary: {e}",
                log_message=f"SalaryIntent.get_effective_salary: {e}",
                exception=e,
            )

    def get_expenses(self) -> IntentResult:
        """Return all recurring expenses."""
        return self._data_source.get_all_expenses()

    def save_expense(self, expense: RecurringExpense) -> IntentResult:
        """Persist a new or updated recurring expense."""
        return self._data_source.save_expense(expense)

    def save_expense_from_dict(self, data: dict) -> IntentResult:
        """Create or update a recurring expense from a plain dict."""
        expense_id = data.get("id")
        if expense_id:
            result = self.get_expenses()
            if result.was_intent_successful and result.data:
                existing = next((e for e in result.data if e.id == expense_id), None)
                if existing:
                    for k, v in data.items():
                        if k != "id" and not k.startswith("_"):
                            setattr(existing, k, v)
                    return self.save_expense(existing)
        clean = {k: v for k, v in data.items() if k != "id" and not k.startswith("_")}
        return self.save_expense(RecurringExpense(**clean))

    def delete_expense(self, expense_id: int) -> IntentResult:
        """Remove a recurring expense by id."""
        return self._data_source.delete_expense_by_id(expense_id)

    def get_field_requirements(self) -> IntentResult:
        """Return field metadata derived from the RecurringExpense model schema."""
        fields = {}
        for name, field_info in RecurringExpense.model_fields.items():
            if name == "id" or name.endswith("_id"):
                continue
            annotation = field_info.annotation
            origin = getattr(annotation, "__origin__", None)
            if origin is list:
                continue
            label = field_info.description or name.replace("_", " ").title()
            fields[name] = {
                "required": field_info.is_required(),
                "label": label,
            }
        return IntentResult(was_intent_successful=True, data=fields)

