"""Integration tests for the RPC dispatch round-trip.

Exercises the real code path the Electron shell uses:

    method string -> dispatch() -> intent -> DB -> to_rpc_dict()/dump() -> JSON

Catches detached-instance errors, missing modules, serialisation bugs, and
data-shape mismatches between the Python core and the frontend.
"""

import importlib
import json
from decimal import Decimal
from pathlib import Path

import pytest
import sqlmodel

import tuttle.app
import tuttle.app.core.abstractions as abstractions
import tuttle.app_db as app_db_mod
from tuttle.app.core.dispatch import _intents, dispatch
from tuttle.app.core.rpc_utils import reset_all
from tuttle.model import (
    Client,
    Contact,
    Contract,
    ContractType,
    Invoice,
    Project,
    User,
)

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


class TestDemoStartPath:
    """Regression tests for the 'Try with demo data' onboarding flow.

    Mirrors the exact RPC sequence the Electron shell fires when the user
    clicks the button: ensure_demo → users.list → users.switch → get_active.
    Also covers recovery from partial/failed installations.
    """

    def test_full_demo_onboarding_sequence(self, rpc_env):
        """Happy path: the full sequence produces a usable demo session."""
        demo_result = dispatch("users.ensure_demo", {})
        assert_ok(demo_result)
        assert demo_result["data"]["db_file"] == "harry-tuttle.db"

        users = assert_ok(dispatch("users.list", {}))["data"]
        assert any(u["db_file"] == "harry-tuttle.db" for u in users)

        switch = dispatch("users.switch", {"db_file": "harry-tuttle.db"})
        assert_ok(switch)

        active = assert_ok(dispatch("users.get_active", {}))["data"]
        assert active is not None, "get_active must return a user after switch"
        assert active["name"] == "Harry Tuttle"
        assert active["profile"] is not None

    def test_demo_has_projects_and_invoices(self, rpc_env):
        """The demo database must contain non-empty data for the dashboard."""
        dispatch("users.switch", {"db_file": "harry-tuttle.db"})

        projects = assert_ok(dispatch("projects.get_all", {}))["data"]
        assert len(projects) >= 4, "Demo should have at least 4 projects"

        invoices = assert_ok(dispatch("invoicing.get_all", {}))["data"]
        assert len(invoices) >= 4, "Demo should have at least 4 invoices"

    def test_recovery_from_empty_database(self, rpc_env):
        """If the demo DB exists but is empty, ensure_demo reinstalls it."""
        from tuttle.app.users.intent import UsersIntent

        users_intent = UsersIntent()
        db_path = users_intent._app_db.get_user_db_path("harry-tuttle.db")

        # Wipe the database contents but keep the file
        from tuttle.db_schema import ensure_schema

        db_path.unlink(missing_ok=True)
        ensure_schema(f"sqlite:///{db_path}")

        assert not UsersIntent._demo_db_is_populated(db_path)

        result = dispatch("users.ensure_demo", {})
        assert_ok(result)
        assert UsersIntent._demo_db_is_populated(db_path)

        dispatch("users.switch", {"db_file": "harry-tuttle.db"})
        projects = assert_ok(dispatch("projects.get_all", {}))["data"]
        assert len(projects) >= 4

    def test_recovery_from_missing_database(self, rpc_env):
        """If the demo DB file is gone, ensure_demo reinstalls it."""
        from tuttle.app.users.intent import UsersIntent

        users_intent = UsersIntent()
        db_path = users_intent._app_db.get_user_db_path("harry-tuttle.db")
        db_path.unlink(missing_ok=True)

        result = dispatch("users.ensure_demo", {})
        assert_ok(result)
        assert db_path.exists()
        assert UsersIntent._demo_db_is_populated(db_path)

    def test_failed_install_rolls_back_registration(self, rpc_env):
        """If install_demo_data crashes, the registration must not persist."""
        from unittest.mock import patch

        from tuttle.app.users.intent import UsersIntent

        users_intent = UsersIntent()
        db_path = users_intent._app_db.get_user_db_path("harry-tuttle.db")

        # Remove existing demo so ensure_demo attempts a fresh install
        users_intent._app_db.remove_user("harry-tuttle.db")
        db_path.unlink(missing_ok=True)
        reset_all()
        _intents.clear()

        with patch("tuttle.demo.install_demo_data", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                dispatch("users.ensure_demo", {})

        reg = users_intent._app_db.get_user_by_db_file("harry-tuttle.db")
        assert reg is None, "Registration must be rolled back after install failure"

        # Reinstall for other tests
        _intents.clear()
        result = dispatch("users.ensure_demo", {})
        assert_ok(result)
        dispatch("users.switch", {"db_file": "harry-tuttle.db"})


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
    ("dashboard.get_revenue_series", {"granularity": "week", "offset": 0}),
    ("dashboard.get_revenue_series", {"granularity": "month", "offset": -1}),
    ("dashboard.get_revenue_series", {"granularity": "year", "offset": 0}),
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

    def test_all_rpc_computed_props_survive_session_close(self, rpc_env):
        """Every __rpc_computed__ property must be serialisable after the DB
        session closes — catches DetachedInstanceError from lazy-loaded
        relationships accessed inside computed properties."""
        models_routes = [
            (User, "users.get_active"),
            (Contact, "contacts.get_all"),
            (Client, "clients.get_all"),
            (Contract, "contracts.get_all"),
            (Project, "projects.get_all"),
            (Invoice, "invoicing.get_all"),
        ]
        for model_cls, route in models_routes:
            computed = getattr(model_cls, "__rpc_computed__", ())
            if not computed:
                continue
            result = dispatch(route, {})
            assert result["ok"], f"{route} failed: {result.get('error')}"
            items = result["data"]
            if not isinstance(items, list):
                items = [items]
            assert len(items) > 0, f"{route} returned no data"
            for prop in computed:
                for item in items:
                    assert prop in item, f"{model_cls.__name__} missing computed prop '{prop}' after serialisation via {route}"

    def test_deposit_and_final_invoice_serialize(self, rpc_env):
        """A final invoice with linked deposits must serialise without
        DetachedInstanceError when invoicing.get_all runs."""
        dispatch("db.ensure", {})

        engine = sqlmodel.create_engine(f"sqlite:///{abstractions._active_db_path}")
        with sqlmodel.Session(engine) as sess:
            # A contract that does not already carry a schedule from the demo
            # data, so this test owns the whole milestone lifecycle.
            contract = next(
                (c for c in sess.exec(sqlmodel.select(Contract)).all() if c.projects and not c.payment_milestones),
                None,
            )
            assert contract is not None, "No schedule-free contract with projects in demo DB"
            contract.type = ContractType.fixed_price
            contract.rate = None
            contract.fixed_price = Decimal("10000")
            sess.add(contract)
            sess.commit()
            contract_id = contract.id

        reset_all()

        contracts_res = dispatch("contracts.get_all", {})
        assert_ok(contracts_res)
        contracts = contracts_res["data"] or []
        target = next((c for c in contracts if c["id"] == contract_id), None)
        assert target is not None
        project_ids = [p["id"] for p in target.get("projects", [])]
        assert project_ids, "Contract has no projects"
        project_id = project_ids[0]

        reset_all()

        ms_res = dispatch(
            "contracts.save_milestones",
            {
                "contract_id": contract_id,
                "milestones": [
                    {"title": "Upfront", "percentage": 50, "position": 0},
                    {"title": "On delivery", "percentage": 50, "position": 1},
                ],
            },
        )
        assert ms_res["ok"], f"save_milestones failed: {ms_res.get('error')}"

        reset_all()

        ms_list = dispatch(
            "contracts.get_milestones",
            {
                "contract_id": contract_id,
            },
        )
        assert ms_list["ok"], f"get_milestones failed: {ms_list.get('error')}"
        milestones = ms_list["data"]
        assert len(milestones) == 2

        deposit_res = dispatch(
            "invoicing.create_deposit",
            {
                "project_id": project_id,
                "milestone_id": milestones[0]["id"],
                "invoice_date": "2026-06-28",
            },
        )
        assert deposit_res["ok"], f"create_deposit failed: {deposit_res.get('error')}"

        reset_all()

        result = dispatch("invoicing.get_all", {})
        assert result["ok"], f"invoicing.get_all failed after deposit creation: {result.get('error')}"
        data = result["data"]
        deposit = next((i for i in data if i.get("document_type") == "deposit"), None)
        assert deposit is not None, "Deposit invoice not in get_all results"
        assert deposit.get("deposit_deductions") is not None
        assert deposit.get("remaining_balance") is not None
        try:
            json.dumps(deposit)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"Deposit invoice not JSON-serializable: {exc}")

        reset_all()

        deposit2_res = dispatch(
            "invoicing.create_deposit",
            {
                "project_id": project_id,
                "milestone_id": milestones[1]["id"],
                "invoice_date": "2026-06-28",
            },
        )
        assert deposit2_res["ok"], f"create_deposit (last milestone / final) failed: {deposit2_res.get('error')}"

        reset_all()

        result2 = dispatch("invoicing.get_all", {})
        assert result2["ok"], f"invoicing.get_all failed after final invoice creation: {result2.get('error')}"
        data2 = result2["data"]
        final = next((i for i in data2 if i.get("document_type") == "final"), None)
        assert final is not None, "Final invoice not in get_all results — last milestone should auto-create a final invoice"
        assert isinstance(final.get("deposit_deductions"), list)
        assert final.get("remaining_balance") is not None
        try:
            json.dumps(final)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"Final invoice not JSON-serializable: {exc}")

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
            ("contacts", set()),
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

    def test_contact_save_accepts_partial_name(self, rpc_env):
        result = dispatch(
            "contacts.save",
            {"contact": {"first_name": "Solo", "last_name": ""}},
        )
        assert_ok(result)
        assert result["data"]["first_name"] == "Solo"
        assert result["data"]["last_name"] == ""

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
