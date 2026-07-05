"""Batch-commit workflow for document-imported entity graphs."""

import base64
import datetime
import enum
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import sqlmodel
from loguru import logger

from ..core.abstractions import SQLModelDataSourceMixin
from ..core.intent_result import IntentResult
from ...data_dir import get_data_dir
from ...model import (
    Address,
    Contact,
    Client,
    Contract,
    Project,
    Invoice,
    InvoiceItem,
    normalize_vat_rate,
)
from ...time import ContractType


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
        """
        _MODELS = {
            "contacts": Contact,
            "clients": Client,
            "contracts": Contract,
            "projects": Project,
            "invoices": Invoice,
            "invoice_items": InvoiceItem,
        }
        return IntentResult(
            was_intent_successful=True,
            data={
                entity_type: {
                    "required": [name for name, _ in _get_required_fields(model_cls)],
                    "enums": _get_enum_fields(model_cls),
                }
                for entity_type, model_cls in _MODELS.items()
            },
        )

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
        except Exception as e:
            logger.exception("commit_import failed")
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Import failed: {e}",
                log_message=f"ImportsIntent.commit_import: {e}",
                exception=e,
            )


def _validate_import_data(data: dict) -> List[str]:
    """Validate new entities against their SQLModel field definitions before DB insertion.

    Reads each model's ``model_fields`` to determine which fields are required
    (non-Optional, no default). Skips relationship fields and FK IDs.
    Skips items with ``existing_id`` set (those are link/update, not create).
    Returns a list of human-readable error strings (empty = valid).
    """
    _MODELS = {
        "contacts": Contact,
        "clients": Client,
        "contracts": Contract,
        "projects": Project,
        "invoices": Invoice,
    }

    errors: List[str] = []

    for entity_type, model_cls in _MODELS.items():
        required_fields = _get_required_fields(model_cls)
        for item in data.get(entity_type, []):
            if item.get("existing_id"):
                continue

            fields = _model_fields(item, model_cls)
            missing = []
            for field_name, field_label in required_fields:
                val = fields.get(field_name)
                if val is None:
                    missing.append(field_label)

            if missing:
                label = (
                    item.get("title")
                    or item.get("name")
                    or item.get("number")
                    or item.get("ref")
                    or "(untitled)"
                )
                type_name = entity_type.capitalize().rstrip("s")
                errors.append(f'{type_name} "{label}": missing {", ".join(missing)}')

    # Validate nested invoice items
    item_required = _get_required_fields(InvoiceItem)
    for inv in data.get("invoices", []):
        if inv.get("existing_id"):
            continue
        inv_label = inv.get("number") or inv.get("ref") or "(untitled)"
        for idx, line in enumerate(inv.get("items", []), 1):
            fields = _model_fields(line, InvoiceItem)
            missing = []
            for field_name, field_label in item_required:
                val = fields.get(field_name)
                if val is None:
                    missing.append(field_label)
            if missing:
                errors.append(
                    f'Invoice "{inv_label}" item #{idx}: missing {", ".join(missing)}'
                )

            # Plausibility: VAT rate must be a valid fraction
            vat = fields.get("VAT_rate")
            if vat is not None:
                try:
                    normalized = normalize_vat_rate(vat)
                    if normalized > Decimal("0.30"):
                        errors.append(
                            f'Invoice "{inv_label}" item #{idx}: '
                            f"VAT rate {float(normalized):.0%} seems implausibly high"
                        )
                except ValueError as e:
                    errors.append(
                        f'Invoice "{inv_label}" item #{idx}: invalid VAT rate — {e}'
                    )

            # Plausibility: unit_price and quantity must be positive
            unit_price = fields.get("unit_price")
            if unit_price is not None and Decimal(str(unit_price)) < 0:
                errors.append(
                    f'Invoice "{inv_label}" item #{idx}: unit price is negative'
                )
            qty = fields.get("quantity")
            if qty is not None and float(qty) <= 0:
                errors.append(
                    f'Invoice "{inv_label}" item #{idx}: quantity must be positive'
                )

    return errors


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

        label = name.replace("_", " ").title()
        result.append((name, label))
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

    if existing_id:
        entity = session.get(model_cls, existing_id)
        if entity and item.get("update_existing"):
            fields = _model_fields(item, model_cls)
            for k, v in fields.items():
                setattr(entity, k, v)
            if isinstance(entity, Contract):
                _finalize_contract(entity, fields)
            summary["updated"].append(label)
        else:
            summary["linked"].append(label)
        if entity:
            _bind_ref(ref, entity.id, ref_to_id)
        return

    # Resolve cross-ref strings to FK ids
    fields = dict(item)
    for ref_key, fk_field in (ref_fks or {}).items():
        ref_val = fields.pop(ref_key, "")
        if ref_val and ref_val in ref_to_id:
            fields[fk_field] = ref_to_id[ref_val]

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
    """Pin a contract's pricing ``type`` and enforce the type invariant.

    If the import payload did not specify ``type`` explicitly, derive it
    from whichever value column is populated. Then ``validate_pricing``
    becomes the single guard: it requires the value column for the chosen
    type and clears the other, so an ambiguous contract can never be
    committed regardless of what the LLM extracted.
    """
    if "type" not in provided:
        entity.type = (
            ContractType.fixed_price
            if entity.fixed_price and not entity.rate
            else ContractType.time_based
        )
    entity.validate_pricing()


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
        hasattr(annotation, "__supertype__")
        and issubclass(getattr(annotation, "__supertype__", type), Decimal)
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
            v = _coerce_value(v, field_info.annotation)
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
