from ..clients.intent import ClientsIntent
from ..contacts.intent import ContactsIntent
from ..core.abstractions import CrudIntent
from ..core.intent_result import IntentResult

from ...model import Client, Contract, User
from ...tax import get_tax_system


class ContractsIntent(CrudIntent):
    """Handles Contract CRUD intents."""

    entity_type = Contract
    deletion_guards = [
        ("projects", "projects", lambda p: p.title),
        ("invoices", "invoices", lambda i: i.number or f"#{i.id}"),
    ]
    __save_skip__ = {"client", "projects", "invoices"}

    def __init__(self):
        super().__init__()
        self._clients_intent = ClientsIntent()
        self._contacts_intent = ContactsIntent()

    # -- Cross-entity delegates ------------------------------------------------

    def get_all_clients_as_map(self):
        return self._clients_intent.get_all_as_map()

    def get_all_contacts_as_map(self):
        return self._contacts_intent.get_all_as_map()

    def save_client(self, client: Client) -> IntentResult:
        return self._clients_intent._validated_save(client=client)

    def get_default_currency(self) -> IntentResult:
        """Derive default contract currency from the user's operating country."""
        try:
            users = self.query(User)
            country = users[0].operating_country if users else "Germany"
            ts = get_tax_system(country)
            return IntentResult(was_intent_successful=True, data=ts.currency)
        except Exception:
            return IntentResult(was_intent_successful=True, data="EUR")

    # -- Contract-specific logic -----------------------------------------------

    def _validated_save(self, contract: Contract) -> IntentResult:
        is_updating = contract.id is not None
        try:
            contract.validate_pricing()
        except ValueError as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=str(e),
                log_message=f"ContractsIntent._validated_save: {e}",
            )
        try:
            contract.validate_currency()
        except ValueError as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=str(e),
                log_message=f"ContractsIntent._validated_save: {e}",
            )
        try:
            contract.validate_vat()
        except ValueError as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=str(e),
                log_message=f"ContractsIntent._validated_save: {e}",
            )
        result = self.save(contract)
        if not result.was_intent_successful:
            if is_updating:
                old = self.get_by_id(contract.id)
                result.data = old.data if old.was_intent_successful else None
            result.error_msg = self._describe_save_error(result.exception)
            result.log_message_if_any()
        return result

    @staticmethod
    def _describe_save_error(exc) -> str:
        if exc is None:
            return "Failed to save the contract."
        detail = str(getattr(exc, "orig", exc))
        if "UNIQUE" in detail or "duplicate" in detail.lower():
            if "title" in detail:
                return "A contract with this title already exists."
            return "A contract with these details already exists."
        if "NOT NULL" in detail:
            return "A required field is missing."
        if "FOREIGN KEY" in detail or "foreign key" in detail:
            return "The selected client is invalid."
        return "Failed to save the contract."

    toggle_complete_status = CrudIntent.toggle_completed
