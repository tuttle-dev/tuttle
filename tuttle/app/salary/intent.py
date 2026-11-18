"""Business logic for the Salary feature."""

from decimal import Decimal

from ...fx import primary_currency, validate_currency_code
from ...model import OTHER_INCOME_KINDS, Invoice, OtherIncome, RecurringExpense, User
from ...tax_reserves import compute_effective_salary
from ..core.abstractions import Intent, SQLModelDataSourceMixin
from ..core.intent_result import IntentResult
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
        return ""

    def _get_tax_currency(self, country: str) -> str:
        """The currency aggregates are shown in (settings, default: tax system)."""
        return primary_currency(country)

    def get_effective_salary(self) -> IntentResult:
        """Compute the effective salary range."""
        try:
            invoices = self.query(Invoice)
            expenses_result = self._data_source.get_all_expenses()
            expenses = expenses_result.data if expenses_result.was_intent_successful else []
            incomes_result = self._data_source.get_all_other_incomes()
            other_incomes = incomes_result.data if incomes_result.was_intent_successful else []

            country = self._get_country()
            currency = self._get_tax_currency(country)

            salary = compute_effective_salary(
                invoices=invoices,
                expenses=expenses,
                country=country,
                currency=currency,
                other_incomes=other_incomes,
            )
            return IntentResult(
                was_intent_successful=True,
                data={
                    "salary": salary,
                    "currency": currency,
                    "country": country,
                    "country_supported": salary.tax_unavailable_reason is None,
                },
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
        try:
            expense.currency = validate_currency_code(expense.currency)
        except ValueError as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=str(e),
                log_message=f"SalaryIntent.save_expense: {e}",
            )
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

    def get_other_incomes(self) -> IntentResult:
        """Return all income from outside the business."""
        return self._data_source.get_all_other_incomes()

    def save_other_income(self, income: OtherIncome) -> IntentResult:
        """Persist a new or updated other income."""
        error = None
        try:
            income.currency = validate_currency_code(income.currency)
        except ValueError as e:
            error = str(e)
        if error is None and income.kind not in OTHER_INCOME_KINDS:
            error = f"Unknown kind of income: {income.kind}."
        if error is None and Decimal(income.amount) < 0:
            error = "Other income cannot be negative."
        if error is not None:
            return IntentResult(
                was_intent_successful=False,
                error_msg=error,
                log_message=f"SalaryIntent.save_other_income: {error}",
            )
        return self._data_source.save_other_income(income)

    def save_other_income_from_dict(self, data: dict) -> IntentResult:
        """Create or update an other income from a plain dict."""
        clean = {k: v for k, v in data.items() if k != "id" and not k.startswith("_")}
        income_id = data.get("id")
        if income_id:
            result = self.get_other_incomes()
            existing = next((i for i in (result.data or []) if i.id == income_id), None)
            if existing:
                for k, v in clean.items():
                    setattr(existing, k, v)
                return self.save_other_income(existing)
        return self.save_other_income(OtherIncome(**clean))

    def delete_other_income(self, income_id: int) -> IntentResult:
        """Remove an other income by id."""
        return self._data_source.delete_other_income_by_id(income_id)

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
