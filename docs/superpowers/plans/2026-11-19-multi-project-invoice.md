# Multi-project invoice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One time-based invoice can bill several projects of one contract, each line knowing its project and rate, and billed hours stop showing as planned.

**Architecture:** Additive schema (`Project.rate`, `InvoiceItem.project_id`); `Invoice.project_id` stays and is null when lines span projects. The existing multi-timesheet `generate_invoice` becomes per-project aware; `invoiced_ranges_by_tag` also reads item ranges. UI adds an "Also bill" project list, a project select per line, a timesheet picker and a project rate field.

**Tech Stack:** Python 3 / SQLModel / Alembic (`just migrate`), pytest (`uv run pytest`), React + TypeScript (Vite, `ui/`).

**Spec:** `docs/superpowers/specs/2026-11-19-multi-project-invoice-design.md`

## Global Constraints

- Schema changes only via `tuttle/model.py` then `just migrate "<msg>"`; never edit existing `tuttle/migrations/versions/*`.
- One invoice = one contract. Multi-project only for time-based contracts and normal invoices (not deposit/final/reminder/fixed-price).
- Issued documents never change: no migration rewrites existing invoice rows; the saved-invoice editor changes only `InvoiceItem.project_id` (and derived `Invoice.project_id`).
- Single-project invoices behave exactly as today (descriptions not prefixed, `invoice.project_id` set).
- Multi-project line description prefix: `"{project.title}: {original description}"`.
- `Project.rate` description: "Rate for this project, in the contract's unit and currency. Empty uses the contract rate."
- UI strings follow `.ai/rules/i18n.md`; demo data/screenshots use the demo user only.
- Run `uv run pytest --tb=short -q` after each task; commit after each task.

## Review Focus

1. Invoice with two projects where one has no hours in the period: that project is skipped, no empty line, no error.
2. `project_ids` containing projects from two contracts, or a fixed-price contract: clear error, nothing saved.
3. Cancelled multi-project invoice: its hours count as unbilled again (item ranges ignored too).
4. Old invoice lines with `project_id = NULL`: revenue and billed-hours fall back to `invoice.project`.
5. `set_item_projects` with a project from another contract: rejected.

Tests for each are named in the owning task.

---

### Task 1: Schema: project rate and item project

**Files:**
- Modify: `tuttle/model.py` (`Project` ~915, `InvoiceItem` ~1559)
- Create: migration via `just migrate "project rate and invoice item project"`
- Test: `tuttle_tests/test_model.py`

**Interfaces:**
- Produces: `Project.rate: Optional[Decimal]`, `Project.effective_rate -> Optional[Decimal]` (property, added to `__rpc_computed__`), `InvoiceItem.project_id: Optional[int]` (FK `project.id`, `ondelete="SET NULL"`), `InvoiceItem.project: Optional[Project]` (lazy subquery, no back_populates).

- [ ] **Step 1: Failing tests** `test_effective_rate_falls_back_to_contract` (project without rate, contract rate 500 → 500), `test_effective_rate_uses_project_rate` (project rate 650 → 650).
- [ ] **Step 2:** `uv run pytest tuttle_tests/test_model.py -k effective_rate -n0` → FAIL.
- [ ] **Step 3:** Add fields/property; run `just migrate "project rate and invoice item project"`, review the generated script adds exactly the two columns + FK (batch mode for SQLite).
- [ ] **Step 4:** `uv run pytest tuttle_tests/test_model.py tuttle_tests/test_migrations.py tuttle_tests/test_db_schema.py -n0` → PASS.
- [ ] **Step 5:** Commit.

### Task 2: Generator: per-project lines, rates and charges

**Files:**
- Modify: `tuttle/invoicing.py` (`generate_invoice`, `build_charge_items`, fixed-price/deposit/final generators)
- Test: `tuttle_tests/test_invoice.py` (new class `TestMultiProjectInvoice`, reuse `_build_project`, `_tracked_hours`)

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `generate_invoice(timesheets, contract, project: Optional[Project], number, date, charges) -> Invoice` — one time line per timesheet at `timesheet.project.effective_rate`, `project_id` set; description prefixed when timesheets cover >1 project.
  - `assign_invoice_project(invoice: Invoice) -> None` — the rule: all items with a project share one → `invoice.project`/`project_id` = it; several → None; none → unchanged.
  - Per-unit charges on a multi-project invoice: one line per project, quantity = that project's billable quantity, `project_id` set. Flat charges: `project_id` = first timesheet's project. Single-project: unchanged, `project_id` = the project.
  - Fixed-price, deposit, final generators set `project_id` on every item.

- [ ] **Step 1: Failing tests**
  - `test_two_projects_two_rates`: projects A (rate None, contract day rate 500) and B (rate 650) on one contract, 8h each → two lines, unit_price 500 / 650, `project_id`s A/B, `invoice.project_id is None`, descriptions start with `"Test Project #a: "`.
  - `test_single_project_unchanged`: one timesheet → description not prefixed, `invoice.project` is the project, item `project_id` set.
  - `test_per_unit_charge_split_per_project`: daily allowance 30 per_unit, A 8h, B 16h → charge lines qty 1.0 (A) and 2.0 (B) with matching `project_id`s; sum of subtotals per project = project revenue.
  - `test_flat_charge_goes_to_first_project`.
  - `test_assign_invoice_project_rules`: same / mixed / none cases.
- [ ] **Step 2:** `uv run pytest tuttle_tests/test_invoice.py -k MultiProject -n0` → FAIL.
- [ ] **Step 3:** Implement. Note projects in unit tests have no ids: compare by `item.project is X` and set both `project=` and `project_id=`.
- [ ] **Step 4:** `uv run pytest tuttle_tests/test_invoice.py tuttle_tests/test_deposit_invoices.py -n0` → PASS.
- [ ] **Step 5:** Commit.

### Task 3: Billed hours from item ranges (#638)

**Files:**
- Modify: `tuttle/timetracking.py:45` `invoiced_ranges_by_tag`
- Test: `tuttle_tests/test_timetracking.py`

**Interfaces:**
- Produces: `invoiced_ranges_by_tag(invoices)` also adds `(item.start_date, item.end_date)` for each item with both dates, under `(item.project or invoice.project).tag`; skips cancelled invoices and reminders.

- [ ] **Step 1: Failing tests** `test_manual_item_marks_hours_invoiced` (invoice without timesheets, item with project + Jan dates → `drop_invoiced` removes January rows for that tag only), `test_item_without_project_falls_back_to_invoice_project`, `test_cancelled_invoice_items_do_not_count`.
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** `uv run pytest tuttle_tests/test_timetracking.py -n0` → PASS. **Step 5:** commit.

### Task 4: Effective rate in forecasts and KPIs

**Files:**
- Modify: `tuttle/forecasting.py:222` (`revenue_from_calendar`), `tuttle/kpi.py:337` (`planned_revenue`); grep `contract.rate` in `tuttle/` for any other per-project calendar pricing and switch to `project.effective_rate`.
- Modify: per-project invoiced revenue grouping (grep for grouping invoices by `project`/`project_id` in `tuttle/kpi.py`, `tuttle/dataviz.py`, `tuttle/app/dashboard/`, `tuttle/app/projects/`): attribute each item via `item.project_id or invoice.project_id`.
- Test: `tuttle_tests/test_dashboard.py` or `test_invoice_revenue.py`

- [ ] **Step 1: Failing test** `test_calendar_revenue_uses_project_rate`: project rate 650 vs contract 500, 8h day → revenue 650.
- [ ] **Step 2–4:** run FAIL → implement → `uv run pytest --tb=short -q` PASS.
- [ ] **Step 5:** Commit.

### Task 5: Intent: create, manual items, set_item_projects, timesheets

**Files:**
- Modify: `tuttle/app/invoicing/intent.py` (`create`, `create_invoice`, `view_timesheet_for_invoice`, `render_timesheet_for_invoice`, new `set_item_projects`), `tuttle/app/invoicing/data_source.py:95` (`get_timesheet_for_invoice` → `get_timesheets_for_invoice`), `tuttle/model.py` (`Invoice.timesheet_pdf_paths`, `Invoice.project_titles`), `tuttle/invoicing.py:315` (email uses `invoice.project_titles`).
- Test: create `tuttle_tests/test_multi_project_invoice.py` using the `in_memory_db` pattern from `test_contract_charges_db.py`.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces (RPC-visible):
  - `invoicing.create(project_id, ..., project_ids: Optional[list[int]] = None)`: `project_ids` adds sibling projects (deduped with `project_id`); all must share `project_id`'s contract and it must be time-based, else error `"All projects on one invoice must belong to the same time-based contract."`. One timesheet per project with hours; projects without hours skipped; if none have hours, the existing "No time tracking data" error. All timesheets rendered when rendering.
  - `manual_items[i]["project_id"]` optional; manual lines default price `project.effective_rate`; every manual line gets a `project_id` (default the chosen project); then `assign_invoice_project`.
  - `invoicing.set_item_projects(invoice_id: int, item_projects: dict[str, Optional[int]]) -> IntentResult[Invoice]`: keys are item ids as strings; each project must belong to the invoice's contract, else error `"Project does not belong to this invoice's contract."`; then `assign_invoice_project`, save.
  - `Invoice.timesheet_pdf_paths -> list[dict]` (`{"project": title, "path": str}` for each rendered timesheet that exists, in `__rpc_computed__`); `timesheet_pdf_path` stays = first entry's path.
  - `Invoice.project_titles -> str` (computed): `invoice.project.title` if set, else unique item project titles joined with ", ".
  - `view_timesheet_for_invoice(id, timesheet_id: Optional[int] = None)`; `render_timesheet_for_invoice` renders all timesheets.

- [ ] **Step 1: Failing tests**
  - `test_create_bills_two_projects` (A, B same contract, hours monkeypatched via timetracking data source → 2 time lines, 2 timesheets, `project_id` None).
  - `test_create_rejects_other_contract` (Review Focus 2).
  - `test_create_rejects_fixed_price_multi`.
  - `test_project_without_hours_is_skipped` (Review Focus 1).
  - `test_set_item_projects_reassigns_and_derives` (mixed → None; all same → that project).
  - `test_set_item_projects_rejects_foreign_project` (Review Focus 5).
  - `test_project_titles_fallback`.
- [ ] **Step 2:** `uv run pytest tuttle_tests/test_multi_project_invoice.py -n0` → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** `uv run pytest --tb=short -q` → PASS.
- [ ] **Step 5:** Commit.

### Task 6: UI

**Files:**
- Modify: `ui/src/components/invoicing/InvoicingView.tsx` (CreateInvoiceDialog ~359, manual line editor ~738, detail line items ~1324, timesheet tab ~1094, list/detail project display), `ui/src/components/business/ProjectsView.tsx` (form ~402–490), locale files per i18n rule.

**Interfaces:**
- Consumes: Task 5 RPCs/fields; projects RPC returns `rate`, `effective_rate`, `contract_id`.

- [ ] **Step 1:** Create dialog: when selected project's contract is time-based and has other projects, and docType is the normal invoice, show "Also bill" checkboxes (unchecked) of sibling projects; send `project_ids`. In manual mode each line gets a project select (siblings + selected) sent as `project_id`; default unit price = that project's `effective_rate`.
- [ ] **Step 2:** Detail "Line Items": each line shows a project select (contract's projects + "No project"); change calls `invoicing.set_item_projects` then refresh. Show it on sent/paid invoices too (bookkeeping only).
- [ ] **Step 3:** Timesheet tab: when `timesheet_pdf_paths.length > 1`, a select of project titles switches the shown PDF.
- [ ] **Step 4:** Where the UI shows an invoice's project, use `project_titles`.
- [ ] **Step 5:** Project form: optional "Rate" number input, placeholder = contract rate; saved as `rate` (empty → null). Verify the projects save path accepts it.
- [ ] **Step 6:** `cd ui && npm run build` → no type errors. Commit.

### Task 7: Run locally and check

- [ ] **Step 1:** Add to `tuttle/demo.py` one combined invoice for two demo projects of one contract (demo user only). `uv run pytest tuttle_tests/test_demo.py -n0` PASS.
- [ ] **Step 2:** `just dev` with demo data; check: create combined invoice via "Also bill", PDF shows prefixed lines, timesheet picker shows both, line project select reassigns, project rate field saves and is used, dashboard planned hours drop after invoicing.
- [ ] **Step 3:** Full `uv run pytest --tb=short -q`; commit.
