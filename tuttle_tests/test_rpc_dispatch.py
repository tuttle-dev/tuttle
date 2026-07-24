"""Integration tests for the RPC dispatch round-trip.

Exercises the real code path the Electron shell uses:

    method string -> dispatch() -> intent -> DB -> to_rpc_dict()/dump() -> JSON

Catches detached-instance errors, missing modules, serialisation bugs, and
data-shape mismatches between the Python core and the frontend.
"""

import importlib
import json
from pathlib import Path

import pytest

import tuttle.app
import tuttle.app.core.abstractions as abstractions
import tuttle.app_db as app_db_mod
from tuttle.app.core.dispatch import _intents, dispatch
from tuttle.app.core.rpc_utils import reset_all

# ---------------------------------------------------------------------------
# Discover every RPC domain on disk: a subpackage of tuttle.app with intent.py
# ---------------------------------------------------------------------------

_APP_DIR = Path(tuttle.app.__file__).parent


def _discover_domains() -> list[str]:
    """Return the names of every directory under tuttle/app that has intent.py."""
    return sorted(p.parent.name for p in _APP_DIR.glob("*/intent.py") if p.parent.name != "core")


DOMAINS = _discover_domains()


# ---------------------------------------------------------------------------
# Fixture: isolated temp database with demo data
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def rpc_env(tmp_path_factory):
    """Set up an isolated ~/.tuttle with full demo data, return the temp dir."""
    tmp = tmp_path_factory.mktemp("tuttle_rpc")

    orig_app_init = app_db_mod.AppDatabase.__init__

    def _patched_init(self, app_dir=None):
        orig_app_init(self, app_dir=tmp)

    app_db_mod.AppDatabase.__init__ = _patched_init
    abstractions._active_db_path = tmp / "tuttle.db"

    try:
        result = dispatch("db.ensure", {})
        assert result["ok"], f"db.ensure failed: {result}"
        demo_result = dispatch("users.ensure_demo", {})
        assert demo_result["ok"], f"users.ensure_demo failed: {demo_result}"
        yield tmp
    finally:
        app_db_mod.AppDatabase.__init__ = orig_app_init
        abstractions._active_db_path = Path.home() / ".tuttle" / "tuttle.db"
        reset_all()
        _intents.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def assert_ok(result: dict) -> dict:
    """Assert the envelope is a successful {ok, data, error} dict."""
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "ok" in result and "data" in result and "error" in result
    assert result["ok"] is True, f"RPC failed: {result.get('error')}"
    assert result["error"] is None
    json.dumps(result)
    return result


# ---------------------------------------------------------------------------
# 1. Boot lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """The startup sequence the Electron shell runs on every launch."""

    def test_db_ensure(self, rpc_env):
        result = dispatch("db.ensure", {})
        assert_ok(result)

    def test_users_list(self, rpc_env):
        result = dispatch("users.list", {})
        data = assert_ok(result)["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        demo = next((u for u in data if u.get("is_demo")), None)
        assert demo is not None, "Demo user missing from users.list"
        assert demo["db_file"] == "harry-tuttle.db"

    def test_users_get_active(self, rpc_env):
        result = dispatch("users.get_active", {})
        data = assert_ok(result)["data"]
        assert data is not None, "get_active returned None"
        assert "name" in data
        assert "db_file" in data
        assert "is_demo" in data
        assert "profile" in data

    def test_users_get_active_profile_shape(self, rpc_env):
        data = dispatch("users.get_active", {})["data"]
        profile = data["profile"]
        assert profile is not None, "Demo user should have a profile"
        assert "name" in profile
        assert "email" in profile
        assert "address" in profile
        assert isinstance(profile["address"], dict)

    def test_preferences_include_due_date_roundtrip(self, rpc_env):
        save = dispatch(
            "preferences.save",
            {"include_due_date": False},
        )
        assert_ok(save)
        data = dispatch("preferences.get", {})["data"]
        assert data["include_due_date"] is False

        save = dispatch(
            "preferences.save",
            {"include_due_date": True},
        )
        assert_ok(save)
        data = dispatch("preferences.get", {})["data"]
        assert data["include_due_date"] is True


# ---------------------------------------------------------------------------
# 2. Read-only route resolution — every frontend RPC method that fetches data
# ---------------------------------------------------------------------------

READ_ROUTES = [
    "db.ensure",
    "users.list",
    "users.get_active",
    "projects.get_all",
    "projects.get_all_contracts",
    "contracts.get_all",
    "contracts.get_all_clients",
    "clients.get_all",
    "clients.get_all_contacts",
    "contacts.get_all",
    "invoicing.get_all",
    "invoicing.available_templates",
    "invoicing.available_languages",
    "preferences.get",
    "llm.get_config",
    "timetracking.get_summary",
    "timeline.get_events",
    "imports.get_existing_entities",
    "imports.get_field_metadata",
    "contacts.get_field_requirements",
    "clients.get_field_requirements",
    "projects.get_field_requirements",
    "contracts.get_field_requirements",
]


@pytest.mark.parametrize("method", READ_ROUTES)
def test_read_route_resolves(rpc_env, method):
    """Every read route returns a valid {ok, data, error} envelope."""
    result = dispatch(method, {})
    assert_ok(result)


DASHBOARD_ROUTES = [
    ("dashboard.get_kpis", {}),
    ("dashboard.get_monthly_chart_data", {"n_months": 12}),
]


@pytest.mark.parametrize("method,params", DASHBOARD_ROUTES)
def test_dashboard_routes(rpc_env, method, params):
    result = dispatch(method, params)
    assert_ok(result)


# ---------------------------------------------------------------------------
# 3. Serialization: relationship data must be present (not just FK ids)
# ---------------------------------------------------------------------------


class TestSerialization:
    """Entities with __rpc_relationships__ must include expanded relationships."""

    def test_projects_include_contract(self, rpc_env):
        data = dispatch("projects.get_all", {})["data"]
        assert isinstance(data, list) and len(data) > 0
        project = data[0]
        assert "contract" in project, "Project missing 'contract' relationship"
        assert isinstance(project["contract"], dict)
        assert "id" in project["contract"]

    def test_contracts_include_client(self, rpc_env):
        data = dispatch("contracts.get_all", {})["data"]
        assert isinstance(data, list) and len(data) > 0
        contract = data[0]
        assert "client" in contract, "Contract missing 'client' relationship"
        assert isinstance(contract["client"], dict)

    def test_contracts_include_projects(self, rpc_env):
        data = dispatch("contracts.get_all", {})["data"]
        contract = data[0]
        assert "projects" in contract, "Contract missing 'projects' relationship"
        assert isinstance(contract["projects"], list)

    def test_contracts_include_invoices(self, rpc_env):
        data = dispatch("contracts.get_all", {})["data"]
        contract = data[0]
        assert "invoices" in contract, "Contract missing 'invoices' relationship"
        assert isinstance(contract["invoices"], list)

    def test_clients_serialization(self, rpc_env):
        data = dispatch("clients.get_all", {})["data"]
        assert isinstance(data, list) and len(data) > 0
        has_contact = any(isinstance(c.get("invoicing_contact"), dict) for c in data)
        has_address = any(isinstance(c.get("address"), dict) for c in data)
        assert has_contact or has_address, "No client has a contact or address"

    def test_contacts_include_address(self, rpc_env):
        data = dispatch("contacts.get_all", {})["data"]
        assert isinstance(data, list) and len(data) > 0
        contact = data[0]
        assert "address" in contact, "Contact missing 'address' relationship"
        assert isinstance(contact["address"], dict)

    def test_invoices_include_items(self, rpc_env):
        data = dispatch("invoicing.get_all", {})["data"]
        assert isinstance(data, list) and len(data) > 0
        invoice = data[0]
        assert "items" in invoice, "Invoice missing 'items' relationship"
        assert isinstance(invoice["items"], list)

    def test_invoices_include_contract(self, rpc_env):
        data = dispatch("invoicing.get_all", {})["data"]
        invoice = data[0]
        assert "contract" in invoice, "Invoice missing 'contract' relationship"
        assert isinstance(invoice["contract"], dict)

    def test_invoices_computed_properties(self, rpc_env):
        data = dispatch("invoicing.get_all", {})["data"]
        invoice = data[0]
        for prop in ("sum", "total", "status", "due_date"):
            assert prop in invoice, f"Invoice missing computed property '{prop}'"

    def test_full_response_is_json_serializable(self, rpc_env):
        for method in [
            "projects.get_all",
            "contracts.get_all",
            "clients.get_all",
            "contacts.get_all",
            "invoicing.get_all",
        ]:
            result = dispatch(method, {})
            try:
                json.dumps(result)
            except (TypeError, ValueError) as exc:
                pytest.fail(f"{method} response not JSON-serializable: {exc}")


# ---------------------------------------------------------------------------
# 4. Field requirements — model schema exposed to the UI
# ---------------------------------------------------------------------------


class TestFieldRequirements:
    """get_field_requirements() must reflect the model's required fields."""

    @pytest.mark.parametrize(
        "domain,required_fields",
        [
            ("contacts", {"first_name", "last_name"}),
            ("clients", {"name"}),
            ("projects", {"title", "description", "tag", "start_date"}),
            ("contracts", {"title", "start_date", "currency"}),
        ],
    )
    def test_required_fields_match_model(self, rpc_env, domain, required_fields):
        data = assert_ok(dispatch(f"{domain}.get_field_requirements", {}))["data"]
        actual = {name for name, meta in data.items() if meta["required"]}
        assert actual == required_fields

    def test_optional_address_not_required_for_contact(self, rpc_env):
        data = assert_ok(dispatch("contacts.get_field_requirements", {}))["data"]
        for field in ("email", "company"):
            assert field in data
            assert data[field]["required"] is False

    def test_project_end_date_not_required(self, rpc_env):
        data = assert_ok(dispatch("projects.get_field_requirements", {}))["data"]
        assert "end_date" in data
        assert data["end_date"]["required"] is False


class TestCrudSaveBehavior:
    """Regression guards for save rules aligned with the model."""

    def test_contact_save_name_only_without_address(self, rpc_env):
        result = dispatch(
            "contacts.save",
            {
                "contact": {
                    "first_name": "Archibald",
                    "last_name": "Tuttle",
                }
            },
        )
        assert_ok(result)
        saved = result["data"]
        assert saved["first_name"] == "Archibald"
        assert saved["last_name"] == "Tuttle"
        assert saved.get("address") is None or saved.get("address") == {}

    def test_contact_save_rejects_missing_name(self, rpc_env):
        result = dispatch(
            "contacts.save",
            {"contact": {"first_name": "Solo", "last_name": ""}},
        )
        assert result["ok"] is False
        assert result["error"]

    def test_project_save_without_end_date(self, rpc_env):
        contracts = assert_ok(dispatch("contracts.get_all", {}))["data"]
        assert contracts, "Need a contract from demo data"
        contract_id = contracts[0]["id"]
        result = dispatch(
            "projects.save",
            {
                "project": {
                    "title": "Open-ended test project",
                    "tag": "#openended",
                    "description": "No end date",
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "contract_id": contract_id,
                }
            },
        )
        assert_ok(result)
        assert result["data"]["end_date"] is None


# ---------------------------------------------------------------------------
# 5. Domain packaging integrity
#
# The dispatcher resolves "domain.method" by importing tuttle.app.{domain}.intent
# at runtime (importlib). Two failure modes are invisible to the route tests
# above because those run against the source tree with a hand-picked route list:
#
#   1. A domain directory without __init__.py is not a Python package, so both
#      importlib AND PyInstaller's collect_submodules silently skip it.
#   2. The frozen build (tuttle-rpc.spec) may not bundle a dynamically-imported
#      domain, producing "No module named 'tuttle.app.{domain}'" only in the
#      distributed .app — never in dev.
#
# These tests guard both for EVERY domain on disk, so a newly added domain can
# never be silently dropped from dev or the release bundle.
# ---------------------------------------------------------------------------


class TestDomainPackaging:
    def test_domains_discovered(self):
        """Sanity: discovery finds the known domains (and any new ones)."""
        assert "imports" in DOMAINS
        assert "invoicing" in DOMAINS
        assert len(DOMAINS) >= 10

    @pytest.mark.parametrize("domain", DOMAINS)
    def test_domain_is_importable_package(self, domain):
        """Each domain must be a real package with an importable intent module.

        Catches the missing-__init__.py class of bug for ALL domains, mirroring
        exactly what the dispatcher does at runtime.
        """
        pkg_init = _APP_DIR / domain / "__init__.py"
        assert pkg_init.exists(), (
            f"tuttle/app/{domain}/ has intent.py but no __init__.py — it is not "
            f"a package, so the dispatcher and the frozen build will skip it."
        )
        mod = importlib.import_module(f"tuttle.app.{domain}.intent")
        candidates = [
            name
            for name in dir(mod)
            if name.endswith("Intent") and getattr(getattr(mod, name), "__module__", None) == mod.__name__
        ]
        assert len(candidates) == 1, f"tuttle.app.{domain}.intent must define exactly one *Intent class, found {candidates}"

    def test_frozen_build_bundles_every_domain(self):
        """The PyInstaller spec must bundle every dynamically-imported domain.

        Uses the same collect_submodules() the spec relies on. Skips when
        PyInstaller isn't installed (it lives in the 'build' dependency group).
        This is the guard that the original release regression lacked.
        """
        pytest.importorskip("PyInstaller")
        from PyInstaller.utils.hooks import collect_submodules

        bundled = set(collect_submodules("tuttle.app"))
        missing = [f"tuttle.app.{d}.intent" for d in DOMAINS if f"tuttle.app.{d}.intent" not in bundled]
        assert not missing, (
            f"These domains are reachable via the dispatcher but would NOT be "
            f"bundled into the frozen tuttle-rpc binary: {missing}. "
            f"Check tuttle-rpc.spec and the domain's __init__.py."
        )
