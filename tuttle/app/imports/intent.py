"""Batch-commit workflow for document-imported entity graphs."""

import base64
import datetime
import enum
from decimal import Decimal
from typing import Any, Dict, List, Optional

import sqlmodel
from loguru import logger

from ...data_dir import get_data_dir
from ...model import (
    Address,
    Client,
    Contact,
    Contract,
    Invoice,
    InvoiceItem,
    Project,
    TaxCategory,
    normalize_tax_category,
    normalize_vat_rate,
)
from ...time import ContractType
from ..core.abstractions import SQLModelDataSourceMixin
from ..core.intent_result import IntentResult

# Fields that are internal to the import workflow, not part of the model
_IMPORT_META = {
    "ref",
    "existing_id",
    "update_existing",
    "contact_ref",
    "client_ref",
    "contract_ref",
    "project_ref",
    "items",
}

# The entity lists of an import, in the order they are saved.
_ENTITY_MODELS = {
    "contacts": Contact,
    "clients": Client,
    "contracts": Contract,
    "projects": Project,
    "invoices": Invoice,
}

# What a contract must state for its type. The model's defaults for these (an
# hourly unit, a monthly cycle) would be guesses, so the review asks for them.
_CONTRACT_REQUIRED_BY_TYPE = {
    ContractType.time_based: ("rate", "unit", "billing_cycle"),
    ContractType.fixed_price: ("fixed_price",),
}

# How an entity links to another: its reference field, the list the linked
# entity is imported in, that entity's model, the foreign key the link sets,
# whether the link is required, and how messages name the linked entity.
_LINKS = {
    "clients": [("contact_ref", "contacts", Contact, "invoicing_contact_id", False, "invoicing contact")],
    "contracts": [("client_ref", "clients", Client, "client_id", False, "client")],
    "projects": [("contract_ref", "contracts", Contract, "contract_id", True, "contract")],
    "invoices": [
        ("contract_ref", "contracts", Contract, "contract_id", False, "contract"),
        ("project_ref", "projects", Project, "project_id", False, "project"),
    ],
}


class ImportRejected(Exception):
    """The reviewed import cannot be committed as it stands; the message says what to fix."""


class ImportsIntent(SQLModelDataSourceMixin):
    """Commit a reviewed set of extracted entities in dependency order."""

    def __init__(self):
        super().__init__()

    def get_existing_entities(self) -> IntentResult:
        """Return all contacts, clients, contracts, projects for smart-matching."""
        try:
            return IntentResult(
                was_intent_successful=True,
                data={
                    "contacts": [c.to_rpc_dict() for c in self.query(Contact)],
                    "clients": [c.to_rpc_dict() for c in self.query(Client)],
                    "contracts": [c.to_rpc_dict() for c in self.query(Contract)],
                    "projects": [p.to_rpc_dict() for p in self.query(Project)],
                },
            )
        except Exception as ex:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load existing entities for matching: {ex}",
                log_message=f"ImportsIntent.get_existing_entities: {ex}",
                exception=ex,
            )

    def get_field_metadata(self) -> IntentResult:
        """Return field metadata per entity type, derived from model schemas.

        Returns a dict keyed by entity type, each containing:
        - required: list of required field names
        - enums: dict mapping field name → list of allowed values

        Contracts also carry ``required_by_type``: the fields each contract
        type needs on top of ``required``.
        """
        _MODELS = {
            "contacts": Contact,
            "clients": Client,
            "contracts": Contract,
            "projects": Project,
            "invoices": Invoice,
            "invoice_items": InvoiceItem,
        }
        data = {
            entity_type: {
                "required": [name for name, _ in _get_required_fields(model_cls)],
                "enums": _get_enum_fields(model_cls),
            }
            for entity_type, model_cls in _MODELS.items()
        }
        data["contracts"]["required_by_type"] = {
            contract_type.value: list(fields) for contract_type, fields in _CONTRACT_REQUIRED_BY_TYPE.items()
        }
        return IntentResult(was_intent_successful=True, data=data)

    def commit_import(self, data: dict) -> IntentResult:
        """Persist the finalized import graph transactionally.

        Each entity list item has either ``existing_id`` (link/update) or
        not (create new).  Cross-references use ``ref`` strings resolved
        via ``contact_ref``, ``client_ref``, ``contract_ref``.

        If ``invoices`` are present, they are saved after entities with
        their line items. The original PDF (if provided as ``file_base64``)
        is stored at the expected filesystem path.
        """
        # Validate required fields before touching the database
        errors = _validate_import_data(data)
        if errors:
            return IntentResult(
                was_intent_successful=False,
                error_msg="\n".join(errors),
                log_message=f"ImportsIntent.commit_import: validation failed: {errors}",
            )
        try:
            ref_to_id: Dict[str, int] = {}
            summary: Dict[str, List[str]] = {"created": [], "linked": [], "updated": []}

            with self.create_session() as session:
                errors = _link_errors(data, lambda model_cls, entity_id: session.get(model_cls, entity_id) is not None)
                if errors:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg="\n".join(errors),
                        log_message=f"ImportsIntent.commit_import: broken links: {errors}",
                    )

                for item in data.get("contacts", []):
                    _save_entity(
                        session,
                        Contact,
                        item,
                        ref_to_id,
                        summary,
                        nested={"address": Address},
                    )

                for item in data.get("clients", []):
                    _save_entity(
                        session,
                        Client,
                        item,
                        ref_to_id,
                        summary,
                        ref_fks={"contact_ref": "invoicing_contact_id"},
                        nested={"address": Address},
                    )

                for item in data.get("contracts", []):
                    _save_entity(
                        session,
                        Contract,
                        item,
                        ref_to_id,
                        summary,
                        ref_fks={"client_ref": "client_id"},
                    )

                for item in data.get("projects", []):
                    _save_entity(
                        session,
                        Project,
                        item,
                        ref_to_id,
                        summary,
                        ref_fks={"contract_ref": "contract_id"},
                    )

                for item in data.get("invoices", []):
                    _save_invoice(
                        session,
                        item,
                        ref_to_id,
                        summary,
                    )

                session.commit()

            # Store original PDF for imported invoices (after commit so we have IDs)
            file_base64 = data.get("file_base64")
            if file_base64 and data.get("invoices"):
                _store_invoice_pdfs(data["invoices"], ref_to_id, file_base64)

            return IntentResult(was_intent_successful=True, data=summary)
        except ImportRejected as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=str(e),
                log_message=f"ImportsIntent.commit_import: {e}",
            )
        except Exception as e:
            logger.exception("commit_import failed")
            return IntentResult(
                was_intent_successful=False,
                error_msg="The import failed unexpectedly. Details are in the application log.",
                log_message=f"ImportsIntent.commit_import: {e}",
                exception=e,
            )


def _validate_import_data(data: dict) -> List[str]:
    """Validate new entities against their SQLModel field definitions before DB insertion.

    Reads each model's ``model_fields`` to determine which fields are required
    (non-Optional, no default). Skips relationship fields and FK IDs. A
    contract must also state what its type needs (``_CONTRACT_REQUIRED_BY_TYPE``).
    Skips items with ``existing_id`` set (those are link/update, not create).
    Returns a list of human-readable error strings (empty = valid).
    """
    errors: List[str] = []

    for entity_type, model_cls in _ENTITY_MODELS.items():
        required_fields = [name for name, _ in _get_required_fields(model_cls)]
        for item in data.get(entity_type, []):
            if item.get("existing_id"):
                continue
            entity = f'{_type_name(entity_type)} "{_item_label(item)}"'
            try:
                fields = _model_fields(item, model_cls)
            except ValueError as e:
                errors.append(f"{entity}: {e}. Correct it.")
                continue

            names = _required_contract_fields(fields) if model_cls is Contract else required_fields
            missing = [_field_label(name) for name in names if fields.get(name) is None]
            if missing:
                errors.append(f"{entity}: fill in the {_and(missing)}.")

    # Validate nested invoice items
    item_required = _get_required_fields(InvoiceItem)
    for inv in data.get("invoices", []):
        if inv.get("existing_id"):
            continue
        inv_label = inv.get("number") or inv.get("ref") or "(untitled)"
        for idx, line in enumerate(inv.get("items", []), 1):
            try:
                fields = _model_fields(line, InvoiceItem)
            except ValueError as e:
                errors.append(f'Invoice "{inv_label}" item #{idx}: {e}. Correct it.')
                continue
            missing = [field_label for field_name, field_label in item_required if fields.get(field_name) is None]
            if missing:
                errors.append(f'Invoice "{inv_label}" item #{idx}: fill in the {_and(missing)}.')

            # Plausibility: VAT rate must be a valid fraction
            vat = fields.get("VAT_rate")
            if vat is not None:
                try:
                    normalized = normalize_vat_rate(vat)
                    if normalized > Decimal("0.30"):
                        errors.append(
                            f'Invoice "{inv_label}" item #{idx}: VAT rate {float(normalized):.0%} seems implausibly high'
                        )
                except ValueError as e:
                    errors.append(f'Invoice "{inv_label}" item #{idx}: invalid VAT rate — {e}')

            # Plausibility: unit_price and quantity must be positive
            unit_price = fields.get("unit_price")
            if unit_price is not None and Decimal(str(unit_price)) < 0:
                errors.append(f'Invoice "{inv_label}" item #{idx}: unit price is negative')
            qty = fields.get("quantity")
            if qty is not None and float(qty) <= 0:
                errors.append(f'Invoice "{inv_label}" item #{idx}: quantity must be positive')

    return errors


def _type_name(entity_type: str) -> str:
    """ "contracts" → "Contract"."""
    return entity_type.capitalize().rstrip("s")


def _item_label(item: dict) -> str:
    """How messages name an entity of the import."""
    person = f"{item.get('first_name') or ''} {item.get('last_name') or ''}".strip()
    return item.get("title") or item.get("name") or item.get("number") or person or item.get("ref") or "(untitled)"


def _field_label(name: str) -> str:
    """ "VAT_rate" → "VAT rate", "start_date" → "start date"."""
    return name.replace("_", " ")


def _and(words: List[str]) -> str:
    """ "a", "a and b", "a, b and c"."""
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"


def _contract_type(fields: dict) -> ContractType:
    """The contract type the import states, else the one its stated price implies."""
    if fields.get("type"):
        return ContractType(fields["type"])
    return ContractType.fixed_price if fields.get("fixed_price") and not fields.get("rate") else ContractType.time_based


def _required_contract_fields(fields: dict) -> List[str]:
    """The fields a new contract has to state: the model's required ones, then what its type needs.

    The VAT rate is required in the standard category only; outside it, the rate is 0.
    """
    names = [name for name, _ in _get_required_fields(Contract)]
    if normalize_tax_category(fields.get("VAT_category") or TaxCategory.standard) is not TaxCategory.standard:
        names.remove("VAT_rate")
    return names + list(_CONTRACT_REQUIRED_BY_TYPE[_contract_type(fields)])


def _existing_id(ref: Any) -> Optional[int]:
    """The id of an "existing:<id>" reference, -1 for a malformed one, None for any other reference."""
    if not (isinstance(ref, str) and ref.startswith("existing:")):
        return None
    try:
        return int(ref.split(":", 1)[1])
    except ValueError:
        return -1


def _link_errors(data: dict, exists) -> List[str]:
    """The links an import cannot make, each named, so none is silently dropped.

    A link is broken when it points to an entity that is not being imported or
    to an existing record that is gone, and when a required one is empty. A
    match to an existing record that is gone is broken too.
    ``exists(model_cls, entity_id)`` says whether the database holds a record.
    """
    errors: List[str] = []
    for entity_type, model_cls in _ENTITY_MODELS.items():
        for item in data.get(entity_type, []):
            entity = f'{_type_name(entity_type)} "{_item_label(item)}"'
            existing_id = item.get("existing_id")
            if existing_id and not exists(model_cls, existing_id):
                noun = _type_name(entity_type).lower()
                errors.append(
                    f"{entity} is matched to an existing {noun} that no longer exists. Create it as a new record or match another {noun}."
                )
            for ref_key, target_type, target_cls, fk_field, required, noun in _LINKS.get(entity_type, []):
                ref = item.get(ref_key)
                linked_id = _existing_id(ref) if ref else item.get(fk_field)
                article = "an" if noun[0] in "aeiou" else "a"
                if linked_id is not None:
                    if not exists(target_cls, linked_id):
                        errors.append(f"{entity} is linked to {article} {noun} that no longer exists. Link another {noun}.")
                elif ref:
                    if ref not in {t.get("ref") for t in data.get(target_type, [])}:
                        errors.append(
                            f"{entity} is linked to {article} {noun} that is not being imported. Restore that {noun} or link another one."
                        )
                elif required and not existing_id:
                    errors.append(f"{entity} needs {article} {noun}. Link one.")
    return errors


def _resolved_links(item: dict, ref_fks: Optional[Dict[str, str]], ref_to_id: Dict[str, int]) -> Dict[str, int]:
    """Foreign keys for the links of ``item``, which ``_link_errors`` has checked."""
    links = {}
    for ref_key, fk_field in (ref_fks or {}).items():
        ref = item.get(ref_key)
        if ref:
            existing_id = _existing_id(ref)
            links[fk_field] = existing_id if existing_id is not None else ref_to_id[ref]
    return links


def _get_required_fields(model_cls: type) -> List[tuple]:
    """Extract (field_name, label) pairs for required fields from a SQLModel class.

    Uses Pydantic's ``FieldInfo.is_required()`` which returns True when
    there is no default and the type is not Optional.
    Skips id, FK fields (*_id), and List relationships.
    """
    result = []
    for name, field_info in model_cls.model_fields.items():
        if name == "id" or name.endswith("_id"):
            continue
        if not field_info.is_required():
            continue
        annotation = field_info.annotation
        origin = getattr(annotation, "__origin__", None)
        if origin is list:
            continue

        result.append((name, _field_label(name)))
    return result


def _get_enum_fields(model_cls: type) -> Dict[str, List[str]]:
    """Return {field_name: [allowed_values]} for all Enum-typed fields in a model."""
    import enum as _enum

    result = {}
    for name, field_info in model_cls.model_fields.items():
        ann = field_info.annotation
        if isinstance(ann, type) and issubclass(ann, _enum.Enum):
            result[name] = [e.value for e in ann]
    return result


def _save_entity(
    session: sqlmodel.Session,
    model_cls: type,
    item: dict,
    ref_to_id: Dict[str, int],
    summary: Dict[str, List[str]],
    *,
    ref_fks: Optional[Dict[str, str]] = None,
    nested: Optional[Dict[str, type]] = None,
):
    """Create or link a single entity, resolving cross-refs to FK ids."""
    ref = item.get("ref", "")
    existing_id = item.get("existing_id")
    label = _entity_label(model_cls, item)
    links = _resolved_links(item, ref_fks, ref_to_id)

    if existing_id:
        # ``_link_errors`` has checked that the record exists.
        entity = session.get(model_cls, existing_id)
        if item.get("update_existing"):
            fields = _model_fields(item, model_cls)
            for k, v in {**fields, **links}.items():
                setattr(entity, k, v)
            if isinstance(entity, Contract):
                _finalize_contract(entity, fields)
            summary["updated"].append(label)
        else:
            summary["linked"].append(label)
        _bind_ref(ref, entity.id, ref_to_id)
        return

    fields = {**item, **links}

    # Handle nested objects (e.g. address)
    nested_objects = {}
    for rel_name, rel_cls in (nested or {}).items():
        rel_data = fields.pop(rel_name, None)
        if isinstance(rel_data, dict):
            rel_data.pop("id", None)
            nested_objects[rel_name] = rel_cls(**rel_data)

    clean = _model_fields(fields, model_cls)
    entity = model_cls(**clean, **nested_objects)
    if isinstance(entity, Contract):
        _finalize_contract(entity, clean)
    session.add(entity)
    session.flush()
    _bind_ref(ref, entity.id, ref_to_id)
    summary["created"].append(label)


def _finalize_contract(entity: Contract, provided: dict) -> None:
    """Complete an imported contract from what the document states, then check it like one entered by hand.

    Without an explicit ``type``, the type follows from whichever price is
    given. A new contract whose document states no payment term gets none,
    not the model's 31 days, and outside the standard tax category its VAT
    rate is 0. Then the validators of the contract form run: ``validate_pricing``
    requires the price of the type and clears the other, so an ambiguous
    contract is never committed. A contract they reject stops the import
    with a message naming it.
    """
    if "type" not in provided:
        entity.type = _contract_type({"fixed_price": entity.fixed_price, "rate": entity.rate})
    if entity.id is None and "term_of_payment" not in provided:
        entity.term_of_payment = None
    if entity.VAT_rate is None and normalize_tax_category(entity.VAT_category) is not TaxCategory.standard:
        entity.VAT_rate = Decimal(0)
    try:
        entity.validate_pricing()
        entity.validate_workload()
        entity.validate_currency()
        entity.validate_vat()
    except ValueError as e:
        raise ImportRejected(f'Contract "{entity.title}": {e}') from None


def _coerce_value(value: Any, annotation: Any) -> Any:
    """Coerce a JSON value to the expected Python type."""
    if value is None or value == "":
        return None
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())
    if origin is not None and type(None) in args:
        inner = next((a for a in args if a is not type(None)), None)
        if inner is not None:
            return _coerce_value(value, inner)
    if annotation is datetime.date or annotation == datetime.date:
        if isinstance(value, str):
            return datetime.date.fromisoformat(value)
    if annotation is Decimal or (
        hasattr(annotation, "__supertype__") and issubclass(getattr(annotation, "__supertype__", type), Decimal)
    ):
        if isinstance(value, (int, float, str)):
            return Decimal(str(value))
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        if isinstance(value, str):
            return annotation(value)
    return value


def _model_fields(data: dict, model_cls: type) -> dict:
    """Filter a dict to only keys that are valid model fields, excluding meta.

    Coerces date strings and decimals to their Python types.
    """
    valid = set(model_cls.model_fields.keys()) - {"id"}
    result = {}
    for k, v in data.items():
        if k not in valid or k in _IMPORT_META:
            continue
        field_info = model_cls.model_fields.get(k)
        if field_info and field_info.annotation is not None:
            try:
                v = _coerce_value(v, field_info.annotation)
            except (ValueError, ArithmeticError):
                raise ValueError(f"the {_field_label(k)} {v!r} is not valid") from None
        if v is not None:
            result[k] = v
    return result


def _entity_label(model_cls: type, item: dict) -> str:
    name = model_cls.__name__
    title = item.get("title") or item.get("name") or ""
    if not title:
        first = item.get("first_name", "")
        last = item.get("last_name", "")
        title = f"{first} {last}".strip()
    return f"{name}: {title}" if title else name


def _bind_ref(ref: str, entity_id: Optional[int], ref_to_id: Dict[str, int]):
    """Record the ref -> DB id mapping after flush."""
    if ref and entity_id is not None:
        ref_to_id[ref] = entity_id


def _save_invoice(
    session: sqlmodel.Session,
    item: dict,
    ref_to_id: Dict[str, int],
    summary: Dict[str, List[str]],
):
    """Create an Invoice with its InvoiceItems, resolving cross-refs to FK ids."""
    ref = item.get("ref", "")
    line_items_data = item.get("items", [])

    # Resolve contract/project refs
    contract_id = None
    project_id = None
    contract_ref = item.get("contract_ref", "")
    project_ref = item.get("project_ref", "")

    # Handle "existing:123" format from UI direct selection
    if contract_ref.startswith("existing:"):
        contract_id = int(contract_ref.split(":")[1])
    elif contract_ref and contract_ref in ref_to_id:
        contract_id = ref_to_id[contract_ref]

    if project_ref.startswith("existing:"):
        project_id = int(project_ref.split(":")[1])
    elif project_ref and project_ref in ref_to_id:
        project_id = ref_to_id[project_ref]

    # Also allow direct IDs passed from the UI
    if not contract_id:
        contract_id = item.get("contract_id")
    if not project_id:
        project_id = item.get("project_id")

    # Build Invoice fields
    invoice_fields = _model_fields(item, Invoice)
    invoice_fields["contract_id"] = contract_id
    invoice_fields["project_id"] = project_id
    invoice_fields.setdefault("sent", True)
    invoice_fields.setdefault("rendered", True)

    invoice = Invoice(**invoice_fields)
    session.add(invoice)
    session.flush()

    for li_data in line_items_data:
        li_fields = _model_fields(li_data, InvoiceItem)
        li_fields["invoice_id"] = invoice.id
        vat = li_fields.get("VAT_rate")
        if vat is not None:
            li_fields["VAT_rate"] = normalize_vat_rate(vat)
        line_item = InvoiceItem(**li_fields)
        session.add(line_item)

    session.flush()
    _bind_ref(ref, invoice.id, ref_to_id)

    label = f"Invoice: {invoice.number or '(no number)'}"
    summary["created"].append(label)


def _store_invoice_pdfs(
    invoices: List[dict],
    ref_to_id: Dict[str, int],
    file_base64: str,
):
    """Write the original uploaded PDF to the expected filesystem path.

    For a single-invoice import, the same PDF is stored for the invoice.
    The path follows the convention: <data_dir>/Invoices/{number}-{client-slug}.pdf
    Since we may not have the client name at this point, we construct the
    prefix from the invoice number and rely on the Invoice.prefix property
    for future lookups. We store using {number}.pdf as a minimal fallback
    and let the Invoice model's pdf_path property resolve it.
    """
    from ...model import Invoice as InvoiceModel

    invoices_dir = get_data_dir() / "Invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)

    file_bytes = base64.b64decode(file_base64)

    for inv_data in invoices:
        ref = inv_data.get("ref", "")
        inv_id = ref_to_id.get(ref)
        if not inv_id:
            continue

        # We need the invoice's prefix for filename. Load it from DB.
        ds = SQLModelDataSourceMixin()
        with ds.create_session() as session:
            invoice = session.get(InvoiceModel, inv_id)
            if not invoice:
                continue
            file_name = invoice.file_name
            pdf_path = invoices_dir / file_name
            pdf_path.write_bytes(file_bytes)
            logger.info(f"Stored imported invoice PDF at {pdf_path}")
