from decimal import Decimal, InvalidOperation

from ...model import Client, Contract, ContractCharge, User
from ...tax import get_tax_system
from ...time import ChargeBasis
from ..clients.intent import ClientsIntent
from ..contacts.intent import ContactsIntent
from ..core.abstractions import CrudIntent
from ..core.intent_result import IntentResult

# Distinguishes "the payload said charges: []" (clear them) from "the payload
# had no charges key at all" (leave them alone).
_CHARGES_UNCHANGED = object()

_CHARGE_FIELDS = ("description", "unit", "is_active")


def _parse_amount(value) -> Decimal:
    """Coerce a charge amount from JSON into a Decimal.

    The zero/negative check lives in ``Contract.validate_charges`` so that
    every write path shares one rule; this only rejects non-numbers.
    """
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Additional charge amount must be a number, got {value!r}")


def _parse_basis(value) -> ChargeBasis:
    """Coerce a charge basis from JSON into the enum.

    Pydantic does not validate assignments on ``SQLModel(table=True)``
    classes, so a raw string would survive all the way to a comparison
    against ``ChargeBasis`` and silently never match.
    """
    if isinstance(value, ChargeBasis):
        return value
    if value is None:
        return ChargeBasis.per_unit
    try:
        return ChargeBasis(str(value))
    except ValueError:
        raise ValueError(f"Unknown additional charge basis: {value!r}")


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
        self._incoming_charges = _CHARGES_UNCHANGED

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

    def save_from_dict(self, data: dict) -> IntentResult:
        """Save a contract, reconciling its list of additional charges.

        ``CrudIntent.__save_nested__`` understands a single nested object,
        not a list, so the charges are peeled off the payload here and handed
        to ``_validated_save`` — the one place that sees the resolved entity
        before it is written. A payload with no ``charges`` key at all leaves
        existing charges untouched, which the document-import path relies on.
        """
        data = dict(data)
        self._incoming_charges = data.pop("charges", _CHARGES_UNCHANGED)
        try:
            return super().save_from_dict(data)
        finally:
            self._incoming_charges = _CHARGES_UNCHANGED

    def _reconcile_charges(self, contract: Contract, raw_charges: list) -> None:
        """Replace the contract's charges with the incoming rows.

        Rows are matched to existing charges by id so that an edit preserves
        them: a charge keeps its identity, and with it the record of whether
        a one-time fee has already been billed. Rows the payload no longer
        contains are dropped by the delete-orphan cascade.
        """
        existing = {c.id: c for c in contract.charges if c.id is not None}
        kept = []
        for position, raw in enumerate(raw_charges):
            fields = {k: raw[k] for k in _CHARGE_FIELDS if k in raw}
            fields["position"] = position
            fields["amount"] = _parse_amount(raw.get("amount"))
            fields["basis"] = _parse_basis(raw.get("basis"))
            if not (fields.get("unit") or "").strip():
                fields["unit"] = None
            charge = existing.get(raw.get("id"))
            if charge is None:
                charge = ContractCharge(**fields)
            else:
                for key, value in fields.items():
                    setattr(charge, key, value)
            kept.append(charge)
        contract.charges = kept

    def _validated_save(self, contract: Contract) -> IntentResult:
        is_updating = contract.id is not None
        if self._incoming_charges is not _CHARGES_UNCHANGED:
            try:
                self._reconcile_charges(contract, self._incoming_charges or [])
            except ValueError as e:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg=str(e),
                    log_message=f"ContractsIntent._validated_save: {e}",
                )
        try:
            contract.validate_pricing()
        except ValueError as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=str(e),
                log_message=f"ContractsIntent._validated_save: {e}",
            )
        try:
            contract.validate_charges()
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
            return "The selected client or bank account is invalid."
        return "Failed to save the contract."

    toggle_complete_status = CrudIntent.toggle_completed
