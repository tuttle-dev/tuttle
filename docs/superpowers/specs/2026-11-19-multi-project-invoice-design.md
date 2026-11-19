# Invoice several projects of one contract in one invoice (#666)

## Intent

A freelancer works on several projects for the same client and sends that
client one invoice per month. Today an invoice belongs to exactly one project,
so the other projects' work gets typed in by hand under it. Consequences:

- Revenue is booked to the wrong project.
- The other projects' calendar hours stay "planned" forever (#638).

Goal: one invoice covering several projects **of one contract**, with each line
knowing its project, so per-project revenue and billed hours are right.

## Goals

- Create one time-based invoice for a contract that bills several of its
  projects for a period, one line per project from calendar hours.
- Each project may have its own rate; otherwise the contract rate applies.
- Each invoice line can carry a project (generated lines automatically, manual
  lines via a picker in the line editor).
- Hours count as billed whenever a non-cancelled invoice line or timesheet
  covers them for that project. This also fixes #638 for single-project
  manual invoices.

## Non-goals

- Invoices spanning several contracts. A client may have several contracts
  (already supported); each contract gets its own invoice.
- Per-project volume/budget. Budget burn and forecasts stay per contract.
- A contract-merge tool. The user moves projects to one contract with the
  existing project form (`ProjectsView.tsx` contract select).
- A backfill script. The user fixes 3-4 old invoices by hand with the line
  editor's project picker.
- Combined deposit, final, milestone or fixed-price invoices. Those stay
  single-project.
- PDF/template changes.

## Anti-goals

- Issued invoices must not change: existing rows keep their `contract_id` and
  `project_id`; no data migration rewrites them.
- Single-project invoices must look and behave exactly as today (PDF, email,
  deposits, filters).

## Constraints

- Schema changes only via `tuttle/model.py` + `just migrate` (see
  `.ai/rules/schema-migrations.md`).
- Currency, VAT, payment terms, bank account keep coming from the contract.
- No private user data in demo data, screenshots or issues.

## Approaches considered

- **A. Keep `Invoice.project_id`, add `InvoiceItem.project_id` (chosen).**
  Additive. Single-project invoices unchanged; on a combined invoice
  `Invoice.project_id` is null and lines carry the project. Revenue per project
  reads `item.project_id`, falling back to `invoice.project_id`.
- **B. Drop `Invoice.project_id`, derive projects from lines.** One source of
  truth, but needs a data migration of every invoice and rewrites of deposit /
  final matching (`data_source.py:268`, `InvoicingView.tsx:1393-1403,1728`),
  the email template and filters. Rejected: same user-visible result, much more
  churn.
- **Contract scope.** Considered one invoice across several contracts of a
  client; rejected because currency/VAT/terms could conflict. One contract per
  invoice, multiple contracts per client allowed.

## Decided design

### Data model (`tuttle/model.py`, one migration)

- `Project.rate: Optional[condecimal(decimal_places=2)]`, default None.
  Description: "Rate for this project, in the contract's unit and currency.
  Empty uses the contract rate."
- `Project.effective_rate` property: `self.rate if self.rate is not None else
  self.contract.rate`.
- `InvoiceItem.project_id: Optional[int]`, FK `project.id`,
  `ondelete="SET NULL"`, plus relationship `project` (lazy subquery, no
  back_populates needed).
- `Invoice.project_id` stays, already nullable. Null means "several projects".

### Generation (`tuttle/invoicing.py`)

- `generate_invoice(timesheets, contract, project, ...)`: `project` becomes
  `Optional`. Per timesheet, the line uses `timesheet.project.effective_rate`,
  sets `project_id=timesheet.project.id`, and its description is prefixed with
  the project title when the invoice has more than one timesheet
  (PDF option 2: flat table, project in description).
- If all timesheets share one project, `invoice.project_id` is that project;
  otherwise null.
- `generate_fixed_price_invoice`, deposit, final: unchanged, but their lines
  get `project_id` of their project too.

### Intent (`tuttle/app/invoicing/intent.py`)

- `create(...)` gains `project_ids: Optional[list[int]]`. If given with more
  than one id, all must belong to the same, time-based contract; otherwise
  return a clear error. One timesheet per project with hours in the period;
  projects without hours are skipped; error only if none have hours.
- Manual lines: each `manual_items` entry may carry `project_id`; the
  `manual_quantity` path and manual items use `project.effective_rate` as the
  default price.
- Every line created gets `project_id` (default: the invoice's project).

### Billed hours (`tuttle/timetracking.py`)

- `invoiced_ranges_by_tag` additionally adds `(item.start_date, item.end_date)`
  for every line with a project and both dates, under the project's tag. For
  old lines without `project_id`, fall back to `invoice.project`. This marks
  manual-line hours as billed (#638).

### Revenue and rate users

- `forecasting.revenue_from_calendar` uses `project.effective_rate` instead of
  `contract.rate`.
- Wherever revenue is attributed per project from invoices, use
  `item.project_id or invoice.project_id`.
- Places that display `invoice.project` (email template `invoicing.py:315`,
  invoice list/detail in `InvoicingView.tsx`, dashboard) show the joined
  project titles of the lines when `invoice.project` is null.

### UI (`ui/src/components/invoicing/InvoicingView.tsx`, `ProjectsView.tsx`)

- Create invoice dialog: user still picks a project first. If its contract is
  time-based and has other projects, show a checkbox list "Also bill" with
  those projects (unchecked by default). Hidden for deposit/final/fixed-price.
  Sends `project_ids`.
- Line editor: each line gets a project select limited to the invoice
  contract's projects (empty allowed).
- Project form: optional "Rate" field, placeholder shows the contract rate.

### Assigning projects on saved invoices (user decision 1a)

- Saved invoices get a project-only line editor: each line shows a project
  select (contract's projects, empty allowed); amount, dates, text stay
  locked, so the issued document never changes. Works on sent/paid invoices
  too, because it is bookkeeping only.
- New RPC `invoicing.set_item_projects(invoice_id, {item_id: project_id|null})`.
- After saving: if all lines share one project, `invoice.project_id` is that
  project; if they span several, it becomes null; if none have a project, it is
  left as it was.
- Same rule decides `invoice.project_id` when manual lines in the create
  dialog pick different projects.

### Timesheets (user decision 2a)

- A combined invoice gets one timesheet PDF per project (existing layout,
  filename from the project tag). `get_timesheet_for_invoice`,
  `Invoice.timesheet_pdf_path`, `render_timesheet_for_invoice` and the create
  flow handle a list instead of assuming exactly one; the UI lists and opens
  each. (Mail attaches only the invoice today; unchanged.)

### Contract charges (user decision 3a)

- On a combined invoice, per-unit charges are split into one line per project
  (quantity = that project's billable quantity, `project_id` set), so
  per-project revenue sums to the invoice total. Flat/once charges are
  attributed to the first selected project. Single-project invoices unchanged.

### Tests

- Generator: two projects, different rates, one invoice, correct lines,
  `invoice.project_id` null, descriptions prefixed.
- Intent: projects from different contracts rejected; project without hours
  skipped.
- `invoiced_ranges_by_tag`: manual line with project + dates marks hours billed;
  cancelled invoice does not.
- `effective_rate` fallback.
- Migration upgrade/downgrade per project rules.

## Left to the builder

- Exact UI wording/i18n keys (follow `.ai/rules/i18n.md`).
- Where in the forecasting/KPI code invoice revenue is grouped per project, and
  applying the item-level fallback there.
- Demo data: optionally one combined invoice in `tuttle/demo.py` for
  screenshots.
