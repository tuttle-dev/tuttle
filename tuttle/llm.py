"""LLM integration for AI-powered document processing.

Provides configuration management, model discovery, and structured
entity extraction from documents. Supports Ollama (local) and any
OpenAI-API-compatible endpoint via llama_index.
"""

import base64
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class LLMConfig(BaseModel):
    """LLM provider configuration.

    provider is either "ollama" (local, with model discovery) or "openai"
    (any OpenAI-API-compatible endpoint: OpenAI, Anthropic, Together, Groq,
    vLLM, etc.).
    """

    provider: str = Field(default="ollama", description="LLM provider: ollama or openai")
    base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL (Ollama server or OpenAI-compatible endpoint)",
    )
    model: str = Field(default="", description="Selected model name")
    api_key: str = Field(default="", description="API key (required for OpenAI-compatible providers)")
    request_timeout: float = Field(default=600.0, description="LLM request timeout in seconds")


def load_config() -> LLMConfig:
    """Load LLM config from the centralized app.db."""
    from tuttle.app_db import AppDatabase

    db = AppDatabase()
    data = db.get_llm_config()
    # Migrate legacy provider names to the unified "openai" provider.
    if data.get("provider") not in ("ollama", "openai"):
        data["provider"] = "openai"
    return LLMConfig(**data)


def save_config(config: LLMConfig) -> LLMConfig:
    """Persist LLM config to the centralized app.db."""
    from tuttle.app_db import AppDatabase

    db = AppDatabase()
    db.save_llm_config(config.model_dump())
    return config


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------


def get_available_models(base_url: str, provider: str = "ollama", api_key: str = "") -> List[str]:
    """Fetch available model names from the configured provider.

    For Ollama uses ``/api/tags``; for OpenAI-compatible endpoints uses
    ``/v1/models`` (or ``/models`` if *base_url* already ends with ``/v1``).
    """
    if provider == "ollama":
        url = f"{base_url.rstrip('/')}/api/tags"
        try:
            resp = httpx.get(url, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            return [m["name"] for m in models if "name" in m]
        except Exception as e:
            logger.error(f"Failed to fetch models from {url}: {e}")
            raise RuntimeError(f"Could not connect to Ollama at {base_url}: {e}")

    stripped = base_url.rstrip("/")
    url = f"{stripped}/models" if stripped.endswith("/v1") else f"{stripped}/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        resp = httpx.get(url, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        return [m["id"] for m in data.get("data", []) if "id" in m]
    except Exception as e:
        logger.error(f"Failed to fetch models from {url}: {e}")
        raise RuntimeError(f"Could not list models at {base_url}: {e}")


# ---------------------------------------------------------------------------
# Document text extraction
# ---------------------------------------------------------------------------


def _extract_text(file_bytes: bytes, file_name: str) -> str:
    """Extract plain text from a file (PDF or text-based)."""
    lower = file_name.lower()
    if lower.endswith(".pdf"):
        import pymupdf

        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n".join(pages)
    else:
        return file_bytes.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Extraction schemas — flat projections of SQLModel classes (no relationships)
# ---------------------------------------------------------------------------

from pydantic import create_model as _create_model  # noqa: E402

from tuttle.model import (  # noqa: E402
    Address,
    Client,
    Contact,
    Contract,
    Invoice,
    InvoiceItem,
    Project,
    normalize_vat_rate,
)


def _flat_schema(model_cls: type, *, include: Optional[List[str]] = None) -> type:
    """Derive a flat Pydantic BaseModel from a SQLModel class.

    Uses model_fields (which already excludes relationships) and keeps only
    scalar columns. All fields made Optional for partial extraction.
    Field descriptions are preserved so llama_index structured output
    can communicate field semantics to the LLM via the JSON Schema.
    """
    fields: Dict[str, Any] = {}
    for name, field_info in model_cls.model_fields.items():
        if name == "id" or name.endswith("_id"):
            continue
        if include and name not in include:
            continue
        annotation = model_cls.__annotations__.get(name)
        if annotation is None:
            continue
        # Decimal/condecimal emit regex patterns that crash Ollama's
        # SchemaToGrammar; use plain float for LLM extraction instead.
        origin = getattr(annotation, "__origin__", None)
        if annotation is Decimal or (origin is not None and Decimal in getattr(annotation, "__args__", ())):
            annotation = float
        elif hasattr(annotation, "__supertype__") and issubclass(annotation.__supertype__, Decimal):
            annotation = float
        fields[name] = (
            Optional[annotation],
            Field(
                default=None,
                description=field_info.description,
            ),
        )

    return _create_model(f"{model_cls.__name__}Extract", **fields)


_AddressExtract = _flat_schema(Address)
_ContactScalarExtract = _flat_schema(Contact, include=["first_name", "last_name", "company", "email"])


# Contact needs a nested address object (not an FK), so extend the flat schema
class _ContactExtract(_ContactScalarExtract):  # type: ignore[valid-type]
    address: Optional[_AddressExtract] = None  # type: ignore[valid-type]


_ClientScalarExtract = _flat_schema(Client, include=["name", "vat_number"])


class _ClientExtract(_ClientScalarExtract):  # type: ignore[valid-type]
    address: Optional[_AddressExtract] = None  # type: ignore[valid-type]


_ContractExtract = _flat_schema(
    Contract,
    include=[
        "title",
        "type",
        "rate",
        "fixed_price",
        "currency",
        "unit",
        "billing_cycle",
        "volume",
        "signature_date",
        "start_date",
        "end_date",
        "VAT_rate",
        "term_of_payment",
    ],
)
_ProjectExtract = _flat_schema(
    Project,
    include=["title", "tag", "description", "start_date", "end_date"],
)

_InvoiceItemExtract = _flat_schema(
    InvoiceItem,
    include=[
        "start_date",
        "end_date",
        "quantity",
        "unit",
        "unit_price",
        "description",
        "VAT_rate",
    ],
)

_InvoiceExtract = _flat_schema(
    Invoice,
    include=["number", "date", "notes"],
)


class ContactExtractionResult(BaseModel):
    items: List[_ContactExtract]  # type: ignore[valid-type]


class ClientExtractionResult(BaseModel):
    class _Item(BaseModel):
        client: _ClientExtract  # type: ignore[valid-type]
        contact_name_hint: Optional[str] = Field(
            default=None,
            description="Name of the invoicing contact person (for user to link)",
        )

    items: List[_Item]


class ContractExtractionResult(BaseModel):
    class _Item(BaseModel):
        contract: _ContractExtract  # type: ignore[valid-type]
        client_name_hint: Optional[str] = Field(
            default=None,
            description="Name of the client this contract belongs to (for user to link)",
        )

    items: List[_Item]


class ProjectExtractionResult(BaseModel):
    class _Item(BaseModel):
        project: _ProjectExtract  # type: ignore[valid-type]
        contract_title_hint: Optional[str] = Field(
            default=None,
            description="Title of the contract this project belongs to (for user to link)",
        )

    items: List[_Item]


# ---------------------------------------------------------------------------
# LLM instantiation
# ---------------------------------------------------------------------------


def _get_llm(config: LLMConfig):
    """Instantiate a llama_index LLM from config."""
    if config.provider == "ollama":
        from llama_index.llms.ollama import Ollama

        return Ollama(
            model=config.model,
            base_url=config.base_url,
            request_timeout=config.request_timeout,
            thinking=True,
        )

    from llama_index.llms.openai_like import OpenAILike

    return OpenAILike(
        model=config.model,
        api_base=config.base_url,
        api_key=config.api_key or "no-key",
        timeout=config.request_timeout,
        is_chat_model=True,
    )


def _structured_complete(sllm, prompt: str, config: LLMConfig):
    """Call sllm.complete with provider-appropriate kwargs.

    OpenAI-compatible providers may reject tool_choice='required'
    (e.g. Anthropic when thinking is enabled). Passing tool_choice='none'
    forces prompt-based JSON extraction instead.
    See https://github.com/run-llama/llama_index/issues/20790
    """
    kwargs = {}
    if config.provider != "ollama":
        kwargs["tool_choice"] = "none"
    return sllm.complete(prompt, **kwargs)


# ---------------------------------------------------------------------------
# Prompts per entity type
# ---------------------------------------------------------------------------

_PROMPTS = {
    "contact": "Extract all contact information (people or companies) from the following document.\n\n",
    "client": "Extract all client or company entities from the following document.\n\n",
    "contract": "Extract all contracts or service agreements from the following document.\n\n",
    "project": "Extract all project descriptions or work packages from the following document.\n\n",
}

_OUTPUT_CLASSES = {
    "contact": ContactExtractionResult,
    "client": ClientExtractionResult,
    "contract": ContractExtractionResult,
    "project": ProjectExtractionResult,
}


# ---------------------------------------------------------------------------
# Generic document parsing
# ---------------------------------------------------------------------------


def parse_document(
    file_base64: str,
    file_name: str,
    entity_type: str,
    config: Optional[LLMConfig] = None,
) -> List[Dict[str, Any]]:
    """Parse entities from a document using an LLM.

    Args:
        file_base64: Base64-encoded file content.
        file_name: Original file name (for type detection).
        entity_type: One of "contact", "client", "contract", "project".
        config: LLM configuration. Loads from disk if None.

    Returns:
        List of dicts shaped for the corresponding *.save RPC endpoint.
    """
    if config is None:
        config = load_config()

    if not config.model:
        raise ValueError("No LLM model configured. Please set up an LLM in Settings.")

    if entity_type not in _OUTPUT_CLASSES:
        raise ValueError(f"Unsupported entity_type: {entity_type}")

    file_bytes = base64.b64decode(file_base64)
    text = _extract_text(file_bytes, file_name)

    if not text.strip():
        raise ValueError("Document appears to be empty or could not be read.")

    llm = _get_llm(config)
    output_cls = _OUTPUT_CLASSES[entity_type]
    sllm = llm.as_structured_llm(output_cls=output_cls)

    prompt = _PROMPTS[entity_type] + "--- DOCUMENT START ---\n" + text + "\n--- DOCUMENT END ---"

    response = _structured_complete(sllm, prompt, config)
    extracted = response.raw

    if entity_type == "contact":
        return _map_contacts(extracted)
    elif entity_type == "client":
        return _map_clients(extracted)
    elif entity_type == "contract":
        return _map_contracts(extracted)
    elif entity_type == "project":
        return _map_projects(extracted)

    return []


# ---------------------------------------------------------------------------
# Result mappers: convert extraction results to RPC-ready dicts
# ---------------------------------------------------------------------------


def _serialise_date(d) -> str:
    """Coerce date-like values to ISO string."""
    if d is None:
        return ""
    if hasattr(d, "isoformat"):
        return d.isoformat()
    return str(d)


def _map_contacts(result: ContactExtractionResult) -> List[Dict[str, Any]]:
    """Map extracted Contact objects to dicts shaped for contacts.save."""
    results = []
    for c in result.items:
        addr = {}
        if c.address:
            addr = {
                "street": getattr(c.address, "street", "") or "",
                "number": getattr(c.address, "number", "") or "",
                "city": getattr(c.address, "city", "") or "",
                "postal_code": getattr(c.address, "postal_code", "") or "",
                "country": getattr(c.address, "country", "") or "",
            }
        d = {
            "first_name": c.first_name or "",
            "last_name": c.last_name or "",
            "company": c.company or "",
            "email": c.email or "",
            "address": addr,
        }
        results.append(d)
    return results


def _map_clients(result: ClientExtractionResult) -> List[Dict[str, Any]]:
    """Map extracted Client objects to dicts shaped for clients.save."""
    results = []
    for item in result.items:
        d = {"name": getattr(item.client, "name", "") or ""}
        d["vat_number"] = getattr(item.client, "vat_number", "") or ""
        addr = {}
        if item.client.address:
            addr = {
                "street": getattr(item.client.address, "street", "") or "",
                "number": getattr(item.client.address, "number", "") or "",
                "city": getattr(item.client.address, "city", "") or "",
                "postal_code": getattr(item.client.address, "postal_code", "") or "",
                "country": getattr(item.client.address, "country", "") or "",
            }
        d["address"] = addr
        d["contact_name_hint"] = item.contact_name_hint or ""
        results.append(d)
    return results


def _map_contracts(result: ContractExtractionResult) -> List[Dict[str, Any]]:
    """Map extracted Contract objects to dicts for contracts.save."""
    results = []
    for item in result.items:
        c = item.contract
        unit = getattr(c, "unit", None)
        billing_cycle = getattr(c, "billing_cycle", None)
        ctype = getattr(c, "type", None)
        rate = getattr(c, "rate", None)
        vat = getattr(c, "VAT_rate", None)
        vat_normalized: Optional[float] = None
        if vat is not None:
            try:
                vat_normalized = float(normalize_vat_rate(vat))
            except ValueError as e:
                logger.warning(f"LLM extraction returned invalid VAT rate {vat!r}: {e}")
                vat_normalized = None
        fixed_price = getattr(c, "fixed_price", None)
        results.append(
            {
                "title": getattr(c, "title", "") or "",
                "type": ctype.value if ctype else None,
                "rate": float(rate) if rate is not None else None,
                "fixed_price": float(fixed_price) if fixed_price is not None else None,
                "currency": getattr(c, "currency", "") or "",
                "unit": unit.value if unit else "",
                "billing_cycle": billing_cycle.value if billing_cycle else "",
                "volume": getattr(c, "volume", None),
                "signature_date": _serialise_date(getattr(c, "signature_date", None)),
                "start_date": _serialise_date(getattr(c, "start_date", None)),
                "end_date": _serialise_date(getattr(c, "end_date", None)),
                "VAT_rate": vat_normalized,
                "term_of_payment": getattr(c, "term_of_payment", None),
                "client_name_hint": item.client_name_hint or "",
            }
        )
    return results


def _map_projects(result: ProjectExtractionResult) -> List[Dict[str, Any]]:
    """Map extracted Project objects to dicts for projects.save."""
    results = []
    for item in result.items:
        p = item.project
        results.append(
            {
                "title": getattr(p, "title", "") or "",
                "tag": getattr(p, "tag", "") or "",
                "description": getattr(p, "description", "") or "",
                "start_date": _serialise_date(getattr(p, "start_date", None)),
                "end_date": _serialise_date(getattr(p, "end_date", None)),
                "contract_title_hint": item.contract_title_hint or "",
            }
        )
    return results


# ---------------------------------------------------------------------------
# Unified contract-document extraction (all entity types in one pass)
# ---------------------------------------------------------------------------


class _RefContact(_ContactExtract):
    ref: str = Field(description="Internal reference ID, e.g. 'contact_1'")


class _RefClient(_ClientExtract):  # type: ignore[valid-type]
    ref: str = Field(description="Internal reference ID, e.g. 'client_1'")
    contact_ref: Optional[str] = Field(default=None, description="ref of the contact person for this client")


class _RefContract(_ContractExtract):  # type: ignore[valid-type]
    ref: str = Field(description="Internal reference ID, e.g. 'contract_1'")
    client_ref: Optional[str] = Field(default=None, description="ref of the client this contract belongs to")


class _RefProject(_ProjectExtract):  # type: ignore[valid-type]
    ref: str = Field(description="Internal reference ID, e.g. 'project_1'")
    contract_ref: Optional[str] = Field(default=None, description="ref of the contract this project belongs to")


class _RefInvoiceItem(_InvoiceItemExtract):  # type: ignore[valid-type]
    """A single line item on an extracted invoice."""

    pass


class _RefInvoice(_InvoiceExtract):  # type: ignore[valid-type]
    ref: str = Field(description="Internal reference ID, e.g. 'invoice_1'")
    contract_ref: Optional[str] = Field(default=None, description="ref of the contract this invoice belongs to")
    project_ref: Optional[str] = Field(default=None, description="ref of the project this invoice belongs to")
    items: List[_RefInvoiceItem] = Field(
        default_factory=list,
        description="Line items on this invoice",
    )


class DocumentExtractionResult(BaseModel):
    """All entities extracted from a document, with cross-refs."""

    contacts: List[_RefContact] = Field(description="People mentioned, e.g. signatories or contact persons")
    clients: List[_RefClient] = Field(description="Companies or organisations that are the contracting party")
    contracts: List[_RefContract] = Field(description="Contractual agreements")
    projects: List[_RefProject] = Field(description="Project descriptions or work packages")
    invoices: List[_RefInvoice] = Field(
        default_factory=list,
        description="Invoices found in the document, each with line items (number, date, amounts)",
    )


def _describe_entity_fields(model_cls: type, skip: set = {"ref"}) -> str:  # noqa: B006
    """Build a field-list description from a Pydantic model's Field metadata."""
    parts = []
    for name, info in model_cls.model_fields.items():
        if name in skip or name.endswith("_ref"):
            continue
        if name == "items":
            continue
        desc = info.description
        parts.append(f"{name} ({desc})" if desc else name)
    return ", ".join(parts)


def _build_summary_prompt() -> str:
    """Generate the Pass-1 summary prompt from the extraction model definitions."""
    sections = []
    for label, model_cls in DocumentExtractionResult.model_fields.items():
        field_info = DocumentExtractionResult.model_fields[label]
        entity_desc = field_info.description or label
        annotation = field_info.annotation
        item_type = getattr(annotation, "__args__", (None,))[0]  # type: ignore[index]
        fields = _describe_entity_fields(item_type)
        sections.append(f"{label.upper()} — {entity_desc}:\n  For each, extract: {fields}")

    return (
        "You are analysing a business document (contract, invoice, or other) for a freelancer.\n"
        "Read the document carefully and list ALL facts relevant to the following categories.\n"
        "Be thorough — include every detail you can find, even if approximate.\n"
        "If the document is an invoice, extract all line items with their quantities and amounts.\n\n"
        + "\n\n".join(sections)
        + "\n\nFormat all dates as YYYY-MM-DD. "
        "Write one fact per line. Do not omit any details.\n\n"
    )


_DOC_SUMMARY_PROMPT = _build_summary_prompt()

_DOC_EXTRACT_PROMPT = (
    "Convert the following entity summary into structured JSON.\n"
    "Use ref strings (contact_1, client_1, contract_1, project_1) to cross-link entities.\n"
    "Populate EVERY field you can; only use null for truly unknown values.\n"
    "Dates must be YYYY-MM-DD.\n\n"
)


_IMPORT_STEPS = [
    {"key": "load_config", "label": "Loading LLM configuration"},
    {"key": "read_document", "label": "Reading document"},
    {"key": "connect_llm", "label": "Connecting to LLM"},
    {"key": "summarize_document", "label": "Analysing document"},
    {"key": "extract_entities", "label": "Extracting structured entities"},
    {"key": "map_results", "label": "Processing results"},
]


def parse_document_for_import(
    file_base64: str,
    file_name: str,
    config: Optional[LLMConfig] = None,
) -> Dict[str, Any]:
    """Extract all entity types from a contract document in a single LLM call.

    Returns a dict with keys:
    - steps: list of {key, label, status, error?} tracking pipeline progress
    - contacts, clients, contracts, projects (when successful)
    """
    steps = [{**s, "status": "pending", "error": None} for s in _IMPORT_STEPS]

    def _mark(key: str, status: str, error: str | None = None):
        for s in steps:
            if s["key"] == key:
                s["status"] = status
                if error:
                    s["error"] = error
                break

    def _fail(key: str, error: str) -> Dict[str, Any]:
        _mark(key, "error", error)
        return {"steps": steps}

    # Step 1: Load config
    _mark("load_config", "running")
    try:
        if config is None:
            config = load_config()
        if not config.model:
            return _fail(
                "load_config",
                "No LLM model configured. Please set up an LLM in Settings.",
            )
        _mark("load_config", "done")
    except Exception as e:
        logger.exception("parse_document_for_import: load_config failed")
        return _fail("load_config", str(e))

    # Step 2: Read document
    _mark("read_document", "running")
    try:
        file_bytes = base64.b64decode(file_base64)
        text = _extract_text(file_bytes, file_name)
        if not text.strip():
            return _fail(
                "read_document",
                "Document appears to be empty or could not be read.",
            )
        _mark("read_document", "done")
    except Exception as e:
        logger.exception("parse_document_for_import: read_document failed")
        return _fail("read_document", f"Could not read document: {e}")

    # Step 3: Connect to LLM
    _mark("connect_llm", "running")
    try:
        llm = _get_llm(config)
        _mark("connect_llm", "done")
    except Exception as e:
        logger.exception("parse_document_for_import: connect_llm failed")
        return _fail("connect_llm", f"Could not connect to LLM: {e}")

    text_len = len(text)
    est_tokens = text_len // 4
    diag = (
        f"model={config.model}, base_url={config.base_url}, "
        f"text={text_len} chars (~{est_tokens} tokens), "
        f"timeout={config.request_timeout}s"
    )

    def _classify_llm_error(e: Exception, elapsed: float, step_key: str):
        msg = str(e)
        low = msg.lower()
        if "timed out" in low or "timeout" in low:
            msg = (
                f"LLM request timed out after {elapsed:.0f}s. Try a faster model or increase the timeout in Settings. ({msg})"
            )
        elif "disconnected" in low or "remoteprotocolerror" in low or "connection reset" in low:
            msg = (
                f"The LLM server disconnected after {elapsed:.0f}s. "
                f"This usually means the model crashed (out of memory). "
                f"Check the server logs, try a smaller model, "
                f"or reduce the context window. "
                f"[{config.model} @ {config.base_url}, ~{est_tokens} tokens]"
            )
        elif "connection" in low or "refused" in low:
            msg = f"Could not reach the LLM server. Is it running? ({msg})"
        return _fail(step_key, msg)

    # Step 4a: Summarise document (plain LLM, no schema constraint)
    _mark("summarize_document", "running")
    logger.info(f"Pass 1 — summarise starting: {diag}")
    t0 = time.monotonic()
    try:
        summary_prompt = _DOC_SUMMARY_PROMPT + "--- DOCUMENT START ---\n" + text + "\n--- DOCUMENT END ---"
        summary_response = llm.complete(summary_prompt)
        summary_text = str(summary_response)
        elapsed = time.monotonic() - t0
        logger.info(f"Pass 1 — summarise completed in {elapsed:.1f}s ({len(summary_text)} chars)")
        logger.info(f"Summary:\n{summary_text[:3000]}")
        _mark("summarize_document", "done")
    except Exception as e:
        elapsed = time.monotonic() - t0
        logger.exception(f"Pass 1 failed after {elapsed:.1f}s: {diag}")
        return _classify_llm_error(e, elapsed, "summarize_document")

    # Step 4b: Extract structured entities from the summary
    _mark("extract_entities", "running")
    logger.info("Pass 2 — structured extraction starting")
    t1 = time.monotonic()
    try:
        sllm = llm.as_structured_llm(output_cls=DocumentExtractionResult)
        extract_prompt = _DOC_EXTRACT_PROMPT + "--- SUMMARY START ---\n" + summary_text + "\n--- SUMMARY END ---"
        response = _structured_complete(sllm, extract_prompt, config)
        elapsed = time.monotonic() - t1
        raw_text = response.text
        logger.info(f"Pass 2 — extraction completed in {elapsed:.1f}s ({len(raw_text)} chars)")
        logger.info(f"LLM raw response: {raw_text[:2000]}")
        extracted: DocumentExtractionResult = response.raw
        logger.info(
            f"Parsed extraction: "
            f"contacts={len(extracted.contacts)}, "
            f"clients={len(extracted.clients)}, "
            f"contracts={len(extracted.contracts)}, "
            f"projects={len(extracted.projects)}, "
            f"invoices={len(extracted.invoices)}"
        )
        _mark("extract_entities", "done")
    except Exception as e:
        elapsed = time.monotonic() - t1
        logger.exception(f"Pass 2 failed after {elapsed:.1f}s: {diag}")
        return _classify_llm_error(e, elapsed, "extract_entities")

    # Step 5: Map results
    _mark("map_results", "running")
    try:
        result = _map_document_extraction(extracted)
        _mark("map_results", "done")
    except Exception as e:
        logger.exception("parse_document_for_import: map_results failed")
        return _fail("map_results", f"Failed to process LLM output: {e}")

    return {"steps": steps, **result}


def _has_content(d: Dict[str, Any], ignore: set = {"ref"}) -> bool:
    """True if the dict has at least one non-null, non-empty value beyond ignored keys."""
    for k, v in d.items():
        if k in ignore:
            continue
        if v is None or v == "" or v == 0:
            continue
        if isinstance(v, dict) and not _has_content(v, ignore=set()):
            continue
        return True
    return False


def _dump_extracted(items: list) -> List[Dict[str, Any]]:
    """Serialise a list of Pydantic extraction models to dicts.

    Coerces date fields via ``_serialise_date`` for frontend convenience.
    Drops skeleton items where only the ref is populated.
    """
    results = []
    for item in items:
        d = item.model_dump()
        for k in list(d):
            if k.endswith("_date"):
                d[k] = _serialise_date(d[k])
        if _has_content(d):
            results.append(d)
        else:
            logger.debug(f"Dropping skeleton entity: {d}")
    return results


def _map_document_extraction(
    result: DocumentExtractionResult,
) -> Dict[str, Any]:
    """Convert the unified extraction result to a frontend-ready dict."""
    mapped = {
        "contacts": _dump_extracted(result.contacts),
        "clients": _dump_extracted(result.clients),
        "contracts": _dump_extracted(result.contracts),
        "projects": _dump_extracted(result.projects),
        "invoices": _map_invoices(result.invoices),
    }
    logger.info("Mapped result counts: " + ", ".join(f"{k}={len(v)}" for k, v in mapped.items()))
    return mapped


def _map_invoices(invoices: list) -> List[Dict[str, Any]]:
    """Map extracted invoice objects to dicts for the frontend."""
    from .model import normalize_vat_rate

    results = []
    for inv in invoices:
        d = inv.model_dump()
        for k in list(d):
            if k.endswith("_date"):
                d[k] = _serialise_date(d[k])
        items = d.get("items", [])
        for item in items:
            for k in list(item):
                if k.endswith("_date"):
                    item[k] = _serialise_date(item[k])
            vat = item.get("VAT_rate")
            if vat is not None:
                try:
                    item["VAT_rate"] = float(normalize_vat_rate(vat))
                except ValueError as e:
                    logger.warning(f"LLM extraction returned invalid invoice item VAT rate {vat!r}: {e}")
                    item["VAT_rate"] = None
        if _has_content(d, ignore={"ref", "items"}):
            results.append(d)
        elif items and any(_has_content(i) for i in items):
            results.append(d)
        else:
            logger.debug(f"Dropping skeleton invoice: {d}")
    return results


# ---------------------------------------------------------------------------
# Legacy function kept for backward compat (wraps parse_document)
# ---------------------------------------------------------------------------


def parse_contacts_from_document(
    file_base64: str,
    file_name: str,
    config: Optional[LLMConfig] = None,
) -> List[Dict[str, Any]]:
    """Parse contact information from a document (legacy wrapper)."""
    return parse_document(file_base64, file_name, "contact", config)
