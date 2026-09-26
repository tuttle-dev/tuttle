"""Integration tests for the RPC dispatch round-trip.

Exercises the real code path the Electron shell uses:

    method string -> dispatch() -> intent -> DB -> to_rpc_dict()/dump() -> JSON

Catches detached-instance errors, missing modules, serialisation bugs, and
data-shape mismatches between the Python core and the frontend.
"""

import datetime
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
    TaxCategory,
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

        with patch("tuttle.app.users.intent.install_demo_data", side_effect=RuntimeError("boom")):
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

    def test_deposit_and_final_invoice_lifecycle(self, rpc_env):
        """Walk a fixed-price contract through its whole payment schedule:
        two deposits, the final invoice deducting both, and settling the chain.

        The serialisation assertions guard against DetachedInstanceError, which
        is what a deposit chain provokes when `invoicing.get_all` runs. The
        second deposit matters on its own: the settlement once dropped every
        deposit but the newest, because writing the milestone flags merged a
        stale contract graph over the links that had just been made.
        """
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
            # Pinned rather than inherited: the deduction amounts asserted below
            # are only meaningful against a known VAT treatment.
            contract.VAT_rate = Decimal("0.19")
            contract.VAT_category = TaxCategory.standard
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
                    {"title": "Upfront", "percentage": 40, "position": 0},
                    {"title": "On commissioning", "percentage": 40, "position": 1},
                    {"title": "On delivery", "percentage": 20, "position": 2},
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
        assert len(milestones) == 3

        for milestone in milestones[:2]:
            deposit_res = dispatch(
                "invoicing.create_deposit",
                {
                    "project_id": project_id,
                    "milestone_id": milestone["id"],
                    "invoice_date": "2026-06-28",
                },
            )
            assert deposit_res["ok"], f"create_deposit failed: {deposit_res.get('error')}"
            reset_all()

        result = dispatch("invoicing.get_all", {})
        assert result["ok"], f"invoicing.get_all failed after deposit creation: {result.get('error')}"
        data = result["data"]
        deposits = [i for i in data if i.get("document_type") == "deposit" and i["project_id"] == project_id]
        assert len(deposits) == 2, "Both deposit invoices should be in get_all results"
        for deposit in deposits:
            # 40% of 10,000 at 19% VAT.
            assert Decimal(str(deposit["remaining_balance"])) == Decimal("4760")
            assert deposit.get("deposit_deductions") == []
            try:
                json.dumps(deposit)
            except (TypeError, ValueError) as exc:
                pytest.fail(f"Deposit invoice not JSON-serializable: {exc}")

        final_res = dispatch(
            "invoicing.create_deposit",
            {
                "project_id": project_id,
                "milestone_id": milestones[2]["id"],
                "invoice_date": "2026-06-28",
            },
        )
        assert final_res["ok"], f"create_deposit (last milestone / final) failed: {final_res.get('error')}"

        reset_all()

        result2 = dispatch("invoicing.get_all", {})
        assert result2["ok"], f"invoicing.get_all failed after final invoice creation: {result2.get('error')}"
        data2 = result2["data"]
        # Project-scoped: the demo data ships a settled milestone contract of
        # its own, whose final invoice would otherwise be picked up here.
        final = next(
            (i for i in data2 if i.get("document_type") == "final" and i["project_id"] == project_id),
            None,
        )
        assert final is not None, "Final invoice not in get_all results — last milestone should auto-create a final invoice"
        deductions = final.get("deposit_deductions")
        assert isinstance(deductions, list)
        assert len(deductions) == 2, "The settlement must deduct every deposit of the contract"
        # 11,900 gross less two 4,760 deposits leaves the closing 20% instalment.
        assert Decimal(str(final["remaining_balance"])) == Decimal("2380")
        try:
            json.dumps(final)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"Final invoice not JSON-serializable: {exc}")

        reset_all()

        # Settling the Schlussrechnung settles the contract: its remaining
        # balance is what is left after the deposits, so paying it means the
        # deposits were paid too.
        paid_res = dispatch("invoicing.toggle_paid", {"id": final["id"]})
        assert paid_res["ok"], f"toggle_paid failed: {paid_res.get('error')}"

        reset_all()

        data3 = assert_ok(dispatch("invoicing.get_all", {}))["data"]
        chain = [i for i in data3 if i["id"] == final["id"] or i.get("deposit_for_id") == final["id"]]
        assert len(chain) == 3, "Expected the final invoice and its two deposits"
        assert all(i["paid"] for i in chain), "Paying the final invoice must settle its deposits"

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

    def test_project_save_without_contract_is_rejected_plainly(self, rpc_env):
        """The form sends contract_id: null; the user must not see pydantic-speak."""
        result = dispatch(
            "projects.save",
            {
                "project": {
                    "title": "Contractless test project",
                    "tag": "#contractless",
                    "description": "Must be rejected",
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "contract_id": None,
                }
            },
        )
        assert result["ok"] is False
        assert result["error"] == "Contract is required."

    def test_invoice_create_rejects_missing_invoice_date(self, rpc_env):
        project_id = assert_ok(dispatch("projects.get_all", {}))["data"][0]["id"]
        result = dispatch(
            "invoicing.create",
            {"project_id": project_id, "invoice_date": "", "from_date": "2026-08-01", "to_date": "2026-08-31"},
        )
        assert result["ok"] is False
        assert result["error"] == "Enter a valid invoice date."

    def test_invoice_create_rejects_inverted_billing_period(self, rpc_env):
        project_id = assert_ok(dispatch("projects.get_all", {}))["data"][0]["id"]
        result = dispatch(
            "invoicing.create",
            {"project_id": project_id, "invoice_date": "2026-09-21", "from_date": "2026-08-31", "to_date": "2026-08-01"},
        )
        assert result["ok"] is False
        assert result["error"] == "The billing period ends before it starts."


class TestFinancialGoals:
    """CRUD and progress rules for financial goals (issue #499)."""

    @pytest.fixture(autouse=True)
    def _demo_db(self, rpc_env):
        """Work against the demo user's database regardless of test ordering."""
        assert_ok(dispatch("users.switch", {"db_file": "harry-tuttle.db"}))

    def _goals(self) -> list:
        return assert_ok(dispatch("dashboard.get_financial_goals", {}))["data"]

    def _create(self, title: str, amount: float, target_date: str) -> dict:
        result = dispatch(
            "dashboard.save_financial_goal",
            {"title": title, "target_amount": amount, "target_date": target_date},
        )
        return assert_ok(result)["data"]

    def test_create_goal(self, rpc_env):
        saved = self._create("Test goal", 50000, "2027-12-31")
        assert saved["id"] is not None
        assert saved["title"] == "Test goal"
        assert saved["target_date"] == "2027-12-31"

    def test_update_goal_in_place(self, rpc_env):
        saved = self._create("Original title", 10000, "2027-06-30")
        goal_id = saved["id"]
        before = len(self._goals())

        updated = assert_ok(
            dispatch(
                "dashboard.save_financial_goal",
                {
                    "id": goal_id,
                    "title": "Renamed",
                    "target_amount": 20000,
                    "target_date": "2027-09-30",
                },
            )
        )["data"]

        assert updated["id"] == goal_id, "Update must not create a new row"
        assert updated["title"] == "Renamed"
        assert len(self._goals()) == before, "Update must not add a goal"

    def test_update_coerces_iso_date_string(self, rpc_env):
        """The update path bypasses Pydantic, so the date needs explicit coercion."""
        saved = self._create("Date coercion", 1000, "2027-01-31")
        assert_ok(
            dispatch(
                "dashboard.save_financial_goal",
                {"id": saved["id"], "target_date": "2027-11-30"},
            )
        )
        entry = next(e for e in self._goals() if e["goal"]["id"] == saved["id"])
        # A raw string written to a date column round-trips as something else.
        assert entry["goal"]["target_date"] == "2027-11-30"

    def test_progress_uses_goal_target_year_not_current_ytd(self, rpc_env):
        """A goal due in a future year must not inherit this year's revenue."""
        far_year = datetime.date.today().year + 5
        saved = self._create("Far future goal", 1000, f"{far_year}-12-31")

        entry = next(e for e in self._goals() if e["goal"]["id"] == saved["id"])
        assert entry["ytd_revenue"] == 0, "No invoices exist in that year"
        assert entry["progress"] == 0.0
        assert entry["goal"]["is_reached"] is False

    def test_is_reached_set_once_progress_complete(self, rpc_env):
        """Reaching 100% persists the flag that drives the timeline's success event."""
        this_year = datetime.date.today().year
        probe = self._create("Revenue probe", 1_000_000_000, f"{this_year}-12-31")
        revenue = next(e for e in self._goals() if e["goal"]["id"] == probe["id"])["ytd_revenue"]
        assert revenue > 0, "Demo data should have paid invoices in the current year"

        saved = self._create("Easily reached", revenue / 2, f"{this_year}-12-31")
        entry = next(e for e in self._goals() if e["goal"]["id"] == saved["id"])
        assert entry["progress"] == 1.0
        assert entry["goal"]["is_reached"] is True, "Flag must be set and persisted"

    def test_delete_goal(self, rpc_env):
        saved = self._create("Doomed goal", 5000, "2027-12-31")
        assert_ok(dispatch("dashboard.delete_financial_goal", {"goal_id": saved["id"]}))
        assert all(e["goal"]["id"] != saved["id"] for e in self._goals())


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


# ---------------------------------------------------------------------------
# Timer and manual time tracking
# ---------------------------------------------------------------------------


class TestManualTimeTracking:
    """Start/Stop timer and manual entries, with the exact payloads the UI sends."""

    @pytest.fixture(autouse=True, scope="class")
    def demo_user(self, rpc_env):
        # Manual entries live in the active user's database, so run against the demo user.
        assert_ok(dispatch("users.switch", {"db_file": "harry-tuttle.db"}))

    def test_get_timer_state_initially_stopped(self, rpc_env):
        r = assert_ok(dispatch("timetracking.get_timer_state", {}))
        assert r["data"]["running"] is False

    def test_start_timer(self, rpc_env):
        r = assert_ok(dispatch("timetracking.start_timer", {"tag": "#demo", "title": None}))
        assert r["data"]["started"] is True
        assert "start_time" in r["data"]

    def test_timer_state_while_running(self, rpc_env):
        r = assert_ok(dispatch("timetracking.get_timer_state", {}))
        assert r["data"]["running"] is True
        assert r["data"]["tag"] == "#demo"

    def test_start_while_running_fails(self, rpc_env):
        r = dispatch("timetracking.start_timer", {"tag": "#other"})
        assert r["ok"] is False
        assert "already running" in r["error"].lower()

    def test_stop_timer(self, rpc_env):
        r = assert_ok(dispatch("timetracking.stop_timer", {"tag": "#demo", "title": "", "end_time": None}))
        assert r["data"]["stopped"] is True
        assert r["data"]["duration_hours"] >= 0
        assert r["data"]["entry"]["tag"] == "#demo"
        assert r["data"]["entry"]["source"] == "manual"
        assert r["data"]["entry"]["entry_id"] is not None

    def test_timer_state_after_stop(self, rpc_env):
        r = assert_ok(dispatch("timetracking.get_timer_state", {}))
        assert r["data"]["running"] is False

    def test_stop_when_not_running_fails(self, rpc_env):
        r = dispatch("timetracking.stop_timer", {})
        assert r["ok"] is False
        assert "no timer" in r["error"].lower()

    def test_start_and_discard(self, rpc_env):
        assert_ok(dispatch("timetracking.start_timer", {"tag": "#discard"}))
        r = assert_ok(dispatch("timetracking.discard_timer", {}))
        assert r["data"]["discarded"] is True
        state = assert_ok(dispatch("timetracking.get_timer_state", {}))
        assert state["data"]["running"] is False

    def test_stop_without_project_needs_a_project(self, rpc_env):
        assert_ok(dispatch("timetracking.start_timer", {"tag": None, "title": None}))
        r = dispatch("timetracking.stop_timer", {"tag": "", "title": "", "end_time": None})
        assert r["ok"] is False
        assert "choose a project" in r["error"].lower()
        # The timer keeps running; assigning the project while running is enough.
        upd = assert_ok(dispatch("timetracking.update_timer", {"tag": "#late"}))
        assert upd["data"]["running"] is True and upd["data"]["tag"] == "#late"
        r = assert_ok(dispatch("timetracking.stop_timer", {"tag": "#late", "title": "Assigned late", "end_time": None}))
        assert r["data"]["entry"]["tag"] == "#late"
        assert r["data"]["entry"]["title"] == "Assigned late"

    def test_stop_with_explicit_end_time(self, rpc_env):
        from datetime import datetime, timedelta

        start = assert_ok(dispatch("timetracking.start_timer", {"tag": "#timed"}))["data"]["start_time"]
        end = (datetime.fromisoformat(start) + timedelta(hours=2)).isoformat()
        r = assert_ok(dispatch("timetracking.stop_timer", {"tag": "#timed", "title": "", "end_time": end}))
        assert r["data"]["duration_hours"] == 2.0

    def test_stop_with_tag_override(self, rpc_env):
        assert_ok(dispatch("timetracking.start_timer", {"tag": "#original"}))
        r = assert_ok(dispatch("timetracking.stop_timer", {"tag": "#override"}))
        assert r["data"]["entry"]["tag"] == "#override"

    def test_add_manual_entry(self, rpc_env):
        r = assert_ok(
            dispatch(
                "timetracking.add_manual_entry",
                {
                    "tag": "#manual",
                    "title": "Client meeting",
                    "date": "2026-09-20",
                    "start_time": "09:00",
                    "end_time": "11:30",
                },
            )
        )
        assert r["data"]["added"] is True
        entry = r["data"]["entry"]
        assert entry["tag"] == "#manual"
        assert entry["duration_hours"] == 2.5
        assert entry["source"] == "manual"
        assert entry["date"] == "2026-09-20"

    def test_add_manual_entry_same_start_is_rejected(self, rpc_env):
        r = dispatch(
            "timetracking.add_manual_entry",
            {
                "tag": "#manual",
                "title": None,
                "date": "2026-09-20",
                "start_time": "09:00",
                "end_time": "10:00",
            },
        )
        assert r["ok"] is False
        assert "already have an entry" in r["error"].lower()

    def test_add_manual_entry_without_project_fails(self, rpc_env):
        r = dispatch(
            "timetracking.add_manual_entry",
            {
                "tag": "",
                "title": None,
                "date": "2026-09-20",
                "start_time": "13:00",
                "end_time": "14:00",
            },
        )
        assert r["ok"] is False
        assert "choose a project" in r["error"].lower()

    def test_add_manual_entry_end_before_start_fails(self, rpc_env):
        r = dispatch(
            "timetracking.add_manual_entry",
            {
                "tag": "#fail",
                "title": None,
                "date": "2026-09-20",
                "start_time": "14:00",
                "end_time": "09:00",
            },
        )
        assert r["ok"] is False
        assert "after the start time" in r["error"].lower()

    def test_update_manual_entry(self, rpc_env):
        add_r = assert_ok(
            dispatch(
                "timetracking.add_manual_entry",
                {
                    "tag": "#edit",
                    "title": "Original",
                    "date": "2026-09-19",
                    "start_time": "10:00",
                    "end_time": "12:00",
                },
            )
        )
        entry_id = add_r["data"]["entry"]["entry_id"]
        r = assert_ok(
            dispatch(
                "timetracking.update_manual_entry",
                {
                    "entry_id": entry_id,
                    "tag": "#edited",
                    "title": "Updated",
                    "date": "2026-09-19",
                    "start_time": "10:30",
                    "end_time": "12:00",
                },
            )
        )
        assert r["data"]["updated"] is True
        assert r["data"]["entry"]["entry_id"] == entry_id
        assert r["data"]["entry"]["tag"] == "#edited"
        assert r["data"]["entry"]["title"] == "Updated"
        assert r["data"]["entry"]["duration_hours"] == 1.5
        events = assert_ok(dispatch("timetracking.get_events", {"project_tag": "#edit"}))
        assert events["data"] == []

    def test_delete_manual_entry(self, rpc_env):
        add_r = assert_ok(
            dispatch(
                "timetracking.add_manual_entry",
                {
                    "tag": "#delete",
                    "title": None,
                    "date": "2026-09-18",
                    "start_time": "08:00",
                    "end_time": "09:00",
                },
            )
        )
        entry_id = add_r["data"]["entry"]["entry_id"]
        r = assert_ok(dispatch("timetracking.delete_manual_entry", {"entry_id": entry_id}))
        assert r["data"]["deleted"] is True
        events = assert_ok(dispatch("timetracking.get_events", {"project_tag": "#delete"}))
        assert events["data"] == []
        r = dispatch("timetracking.delete_manual_entry", {"entry_id": entry_id})
        assert r["ok"] is False
        assert "no longer exists" in r["error"].lower()

    def test_calendar_data_mixes_timer_and_manual_rows(self, rpc_env):
        r = assert_ok(dispatch("timetracking.get_calendar_data", {"year": 2026, "month": 9, "project_tag": None}))
        data = r["data"]
        assert data["days_in_month"] == 30
        assert "2026-09-20" in data["days"]
        assert all("source" in ev for ev in data["events"])

    def test_imported_entries_have_no_entry_id(self, rpc_env):
        import pandas

        from tuttle.app.timetracking.aggregation import merge_dataframes
        from tuttle.app.timetracking.data_source import TimeTrackingDataFrameSource

        row = pandas.DataFrame(
            [
                {
                    "title": "Standup",
                    "tag": "#cal",
                    "description": "",
                    "duration": pandas.Timedelta(hours=1),
                    "all_day": False,
                    "end": pandas.Timestamp("2026-09-15T10:00", tz="CET"),
                    "source": "calendar",
                }
            ],
            index=pandas.DatetimeIndex([pandas.Timestamp("2026-09-15T09:00", tz="CET")], name="begin"),
        )
        ds = TimeTrackingDataFrameSource()
        ds.store_data_frame(merge_dataframes(ds.calendar_rows(), row))
        events = assert_ok(dispatch("timetracking.get_events", {"project_tag": "#cal"}))["data"]
        assert len(events) == 1
        assert events[0]["source"] == "calendar"
        assert events[0]["entry_id"] is None

        r = dispatch(
            "timetracking.update_manual_entry",
            {
                "entry_id": 999999,
                "tag": "#cal",
                "title": None,
                "date": "2026-09-15",
                "start_time": "09:00",
                "end_time": "11:00",
            },
        )
        assert r["ok"] is False
        assert "no longer exists" in r["error"].lower()

    def test_manual_entry_may_share_a_start_with_a_calendar_event(self, rpc_env):
        r = assert_ok(
            dispatch(
                "timetracking.add_manual_entry",
                {
                    "tag": "#manual",
                    "title": None,
                    "date": "2026-09-15",
                    "start_time": "09:00",
                    "end_time": "09:30",
                },
            )
        )
        assert r["data"]["added"] is True
        cal = assert_ok(dispatch("timetracking.get_events", {"project_tag": "#cal"}))["data"]
        assert len(cal) == 1

    def test_disconnecting_calendar_keeps_manual_entries(self, rpc_env):
        assert_ok(dispatch("timetracking.clear", {}))
        events = assert_ok(dispatch("timetracking.get_events", {}))["data"]
        assert events
        assert all(ev["source"] == "manual" for ev in events)

    def test_manual_entries_survive_a_backend_restart(self, rpc_env):
        from tuttle.app.timetracking.data_source import TimeTrackingDataFrameSource

        # A user switch or process restart leaves the in-memory frame empty.
        TimeTrackingDataFrameSource().clear()
        events = assert_ok(dispatch("timetracking.get_events", {}))["data"]
        manual = [ev for ev in events if ev["source"] == "manual"]
        assert manual
        assert all(ev["entry_id"] is not None for ev in manual)

    def test_timesheet_generation_includes_manual_entries(self, rpc_env):
        import datetime

        from tuttle import timetracking
        from tuttle.app.projects.intent import ProjectsIntent
        from tuttle.app.timetracking.intent import TimeTrackingIntent

        project = next(p for p in ProjectsIntent().get_all().data if p.tag and p.contract)
        assert_ok(
            dispatch(
                "timetracking.add_manual_entry",
                {
                    "tag": project.tag,
                    "title": "Manual for invoice",
                    "date": "2026-09-11",
                    "start_time": "09:00",
                    "end_time": "11:00",
                },
            )
        )
        df = TimeTrackingIntent().get_timetracking_data().data
        sheet = timetracking.generate_timesheet(df, project, datetime.date(2026, 9, 1), datetime.date(2026, 9, 30))
        manual_items = [item for item in sheet.items if item.title == "Manual for invoice"]
        assert len(manual_items) == 1
        assert manual_items[0].duration == datetime.timedelta(hours=2)

    def test_empty_month_has_full_calendar_shape(self, rpc_env):
        r = assert_ok(dispatch("timetracking.get_calendar_data", {"year": 2026, "month": 2, "project_tag": None}))
        assert r["data"]["days_in_month"] == 28
        assert r["data"]["first_weekday"] == 6
        assert r["data"]["summary"]["total_events"] == 0

    def test_calendar_cache_round_trips(self, rpc_env):
        import pandas

        from tuttle.app.timetracking.data_source import TimeTrackingDataFrameSource, calendar_cache_path

        row = pandas.DataFrame(
            [
                {
                    "title": "Cached",
                    "tag": "#cache",
                    "description": "",
                    "duration": pandas.Timedelta(hours=1),
                    "all_day": False,
                    "end": pandas.Timestamp("2026-09-16T10:00", tz="CET"),
                    "source": "calendar",
                }
            ],
            index=pandas.DatetimeIndex([pandas.Timestamp("2026-09-16T09:00", tz="CET")], name="begin"),
        )
        path = calendar_cache_path(abstractions.get_active_db())
        original = path.read_bytes() if path.exists() else None
        ds = TimeTrackingDataFrameSource()
        try:
            ds.store_data_frame(row)
            ds.save_to_cache()
            assert path.exists()
            ds.clear()
            assert ds.load_from_cache()
            assert ds.has_calendar_rows()
            assert ds.calendar_rows().index.tz is not None
        finally:
            # This is the demo user's own cache; leave it as the other tests expect.
            if original is not None:
                path.write_bytes(original)
            ds.clear()

    def test_get_project_tags(self, rpc_env):
        r = assert_ok(dispatch("timetracking.get_project_tags", {}))
        assert isinstance(r["data"], list)
        for item in r["data"]:
            assert "tag" in item
            assert "title" in item
