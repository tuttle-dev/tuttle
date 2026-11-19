import { Fragment, useEffect, useId, useState } from "react";
import {
  FileText, XCircle, Plus, Clock, ChevronLeft, ChevronRight, Receipt, Milestone, FileSignature,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num, bool, entity as subEntity, list as entityList } from "../../api/entity";
import { taxCategory, taxTreatment } from "../../api/tax";
import { StepDots } from "../shared/StepDots";
import { Dialog, DialogHeader, DialogBody, DialogFooter } from "../shared/Dialog";
import type { Entity } from "../../api/types";
import { localDateIso } from "../../api/entity";

type DocumentType = "invoice" | "deposit" | "final";

const DOCUMENT_TYPE_OPTIONS = [
  { value: "invoice" as DocumentType, label: "Invoice", icon: FileText },
  { value: "deposit" as DocumentType, label: "Deposit", icon: Milestone },
  { value: "final" as DocumentType, label: "Final", icon: Receipt },
];

interface LineItem {
  description: string;
  quantity: string;
  unit: string;
  unitPrice: string;
}

const UNIT_OPTIONS = ["hour", "day", "piece", "flat"] as const;

const CREATE_INVOICE_STEPS = ["Project", "Details"] as const;

const CHARGE_BASIS_LABELS: Record<string, string> = {
  per_unit: "per billed unit",
  per_invoice: "every invoice",
  once: "once, on the first invoice",
};

function contractOf(project?: Entity | null): Entity | null {
  return project ? subEntity(project, "contract") : null;
}

/** Additional charges the contract will add to the invoice, if any. */
function contractCharges(project?: Entity | null): Entity[] {
  const contract = contractOf(project);
  if (!contract) return [];
  return entityList(contract, "charges").filter((c) => bool(c, "is_active"));
}

/** The contract an invoice bills under, with its terms on hover or focus. */
function ContractPreview({ contract }: { contract: Entity }) {
  const id = useId();
  const client = subEntity(contract, "client");
  const bank = subEntity(contract, "bank_account");
  const currency = str(contract, "currency") || "EUR";
  const fixedPrice = num(contract, "fixed_price");
  const term = str(contract, "term_of_payment");
  const terms: [string, string][] = [
    ["Client", client ? str(client, "name") : "—"],
    fixedPrice > 0
      ? ["Fixed price", `${fixedPrice} ${currency}`]
      : ["Rate", `${num(contract, "rate")} ${currency} per ${str(contract, "unit") || "hour"}`],
    ["VAT", taxTreatment(taxCategory(str(contract, "VAT_category")), num(contract, "VAT_rate"))],
    ["Payment", term ? `${term} days` : "—"],
    ["Bank account", bank ? str(bank, "name") : "Default"],
  ];
  return (
    <span className="relative group flex mt-1.5">
      <button type="button" aria-describedby={id}
        className="w-full flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-xs text-secondary cursor-help hover:text-primary transition-colors focus:outline-none focus:ring-2 focus:ring-accent">
        <FileSignature size={12} className="shrink-0" />
        <span className="truncate">{str(contract, "title")}</span>
        <span className="ml-auto shrink-0 text-tertiary">{currency}</span>
      </button>
      <span id={id} role="tooltip"
        className="absolute top-full left-0 mt-2 z-50 w-64 rounded-md border border-border-subtle bg-bg-card p-3 shadow-lg
          opacity-0 invisible transition-all duration-150
          group-hover:opacity-100 group-hover:visible
          group-focus-within:opacity-100 group-focus-within:visible">
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-xs">
          {terms.map(([label, value]) => (
            <Fragment key={label}>
              <dt className="text-tertiary">{label}</dt>
              <dd className="text-primary min-w-0 break-words">{value}</dd>
            </Fragment>
          ))}
        </dl>
      </span>
    </span>
  );
}

function makeDefaultItem(project?: Entity | null): LineItem {
  const contract = contractOf(project);
  const unit = contract ? str(contract, "unit") : "";
  const rate = contract ? num(contract, "rate") : 0;
  return {
    description: project ? str(project, "title") : "",
    quantity: "",
    unit: unit || "hour",
    unitPrice: rate ? String(rate) : "",
  };
}

/** Manual line items seeded from the project: the rate line plus each charge. */
function makeDefaultItems(project?: Entity | null, charges?: Entity[] | null): LineItem[] {
  const contract = contractOf(project);
  const contractUnit = contract ? str(contract, "unit") || "hour" : "hour";
  const items = [makeDefaultItem(project)];
  for (const charge of charges ?? contractCharges(project)) {
    items.push({
      description: str(charge, "description"),
      quantity: "",
      unit: str(charge, "unit") || (str(charge, "basis") === "per_unit" ? contractUnit : "flat"),
      unitPrice: String(num(charge, "amount")),
    });
  }
  return items;
}

export function CreateInvoiceDialog({ projectId: initialProjectId, onClose, onCreated }: {
  /** The project to start with; the first active one if not given. */
  projectId?: number;
  onClose: () => void;
  onCreated: (newId?: number, warning?: string | null) => Promise<void> | void;
}) {
  const [projects, setProjects] = useState<Entity[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [invoiceDate, setInvoiceDate] = useState(localDateIso);
  const [fromDate, setFromDate] = useState(() => {
    const d = new Date(); d.setMonth(d.getMonth() - 1); d.setDate(1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
  });
  const [toDate, setToDate] = useState(() => {
    const d = new Date(); d.setDate(0);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  });

  function localDateStr(d: Date) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  function setMonth(year: number, month: number) {
    setFromDate(`${year}-${String(month + 1).padStart(2, "0")}-01`);
    const last = new Date(year, month + 1, 0);
    setToDate(localDateStr(last));
  }

  function shiftMonth(delta: number) {
    const cur = new Date(fromDate + "T00:00:00");
    const d = new Date(cur.getFullYear(), cur.getMonth() + delta, 1);
    setMonth(d.getFullYear(), d.getMonth());
  }
  const [mode, setMode] = useState<"timetracking" | "manual">("timetracking");
  const [lineItems, setLineItems] = useState<LineItem[]>([makeDefaultItem()]);
  const [hasTimeData, setHasTimeData] = useState(false);
  const [withTimesheet, setWithTimesheet] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [savedNotes, setSavedNotes] = useState<Entity[]>([]);
  const [selectedNoteIds, setSelectedNoteIds] = useState<Set<number>>(new Set());
  const [customNoteText, setCustomNoteText] = useState("");

  const [docType, setDocType] = useState<DocumentType>("invoice");
  const [selectedMilestoneId, setSelectedMilestoneId] = useState<number | null>(null);
  const [step, setStep] = useState(0);

  const selectedProject = projects.find((p) => p.id === projectId) ?? null;
  const isFixedPrice = selectedProject ? bool(selectedProject, "is_fixed_price") : false;
  const [eligibleCharges, setEligibleCharges] = useState<Entity[] | null>(null);
  const charges = eligibleCharges ?? contractCharges(selectedProject);
  const selectedContract = contractOf(selectedProject);
  const chargeCurrency = (selectedContract ? str(selectedContract, "currency") : "") || "EUR";

  const milestones = selectedContract ? entityList(selectedContract, "payment_milestones") : [];
  const hasMilestones = milestones.length > 0;
  const openMilestones = milestones.filter((m) => !bool(m, "invoiced"));
  const isLastOpenMilestone =
    openMilestones.length === 1 && selectedMilestoneId === openMilestones[0]?.id;
  // A project is settled once: a second final invoice would bill the contract again.
  const isSettled = selectedProject ? bool(selectedProject, "is_settled") : false;
  const canSettle = hasMilestones && openMilestones.length < milestones.length && !isSettled;

  // The document type resets with the project, so a picker option that no
  // longer applies cannot survive into a submission.
  useEffect(() => {
    if (docType === "final" && !canSettle) setDocType("invoice");
  }, [docType, canSettle]);

  // The backend decides which charges a new invoice actually carries — a
  // one-time fee already billed must not be previewed as upcoming.
  useEffect(() => {
    if (projectId == null) { setEligibleCharges(null); return; }
    let cancelled = false;
    (async () => {
      const res = await rpc<Entity[]>("invoicing.get_eligible_charges", { project_id: projectId });
      if (cancelled) return;
      const resolved = res.ok && res.data ? res.data : null;
      setEligibleCharges(resolved);
      if (resolved) {
        const proj = projects.find((p) => p.id === projectId) ?? null;
        setLineItems(makeDefaultItems(proj, resolved));
      }
    })();
    return () => { cancelled = true; };
  }, [projectId]);

  useEffect(() => {
    (async () => {
      const [projRes, ttRes, notesRes] = await Promise.all([
        rpc<Entity[]>("projects.get_all"),
        rpc<{ total_events: number }>("timetracking.get_summary"),
        rpc<Entity[]>("invoice_notes.get_all"),
      ]);
      if (projRes.ok && projRes.data) {
        const active = projRes.data.filter((p) => !bool(p, "is_completed"));
        setProjects(active);
        const first = active.find((p) => p.id === initialProjectId) ?? active[0];
        if (first) {
          setProjectId(first.id);
          setLineItems(makeDefaultItems(first));
        }
      }
      if (ttRes.ok && ttRes.data && ttRes.data.total_events > 0) setHasTimeData(true);
      else setMode("manual");
      if (notesRes.ok && notesRes.data) setSavedNotes(notesRes.data);
    })();
  }, []);

  function handleProjectChange(newId: number) {
    setProjectId(newId);
    const proj = projects.find((p) => p.id === newId) ?? null;
    setLineItems(makeDefaultItems(proj));
    setDocType("invoice");
    setSelectedMilestoneId(null);
  }

  function updateItem(idx: number, patch: Partial<LineItem>) {
    setLineItems((prev) => prev.map((it, i) => i === idx ? { ...it, ...patch } : it));
  }

  function addItem() {
    setLineItems((prev) => [...prev, makeDefaultItem(selectedProject)]);
  }

  function removeItem(idx: number) {
    setLineItems((prev) => prev.length <= 1 ? prev : prev.filter((_, i) => i !== idx));
  }

  const canAdvance = projectId != null && (docType !== "deposit" || selectedMilestoneId != null);

  function itemsValid(): boolean {
    return lineItems.every((it) => {
      const qty = parseFloat(it.quantity);
      const price = parseFloat(it.unitPrice);
      return it.description.trim() && qty > 0 && price >= 0;
    });
  }

  async function submit() {
    if (!projectId) { setError("Select a project"); return; }
    if (!invoiceDate) { setError("Enter an invoice date"); return; }
    if (docType !== "deposit" && docType !== "final") {
      if (!fromDate || !toDate) { setError("Enter the billing period"); return; }
      if (toDate < fromDate) { setError("The billing period ends before it starts"); return; }
    }
    setSubmitting(true);
    setError("");

    // Deposit invoice flow
    if (docType === "deposit") {
      if (!selectedMilestoneId) { setError("Select a milestone"); setSubmitting(false); return; }
      const res = await rpc<{ id?: number }>("invoicing.create_deposit", {
        project_id: projectId,
        milestone_id: selectedMilestoneId,
        invoice_date: invoiceDate,
      });
      if (res.ok) { await onCreated(res.data?.id, res.warning); }
      else { setError(res.error || "Failed to create deposit invoice"); }
      setSubmitting(false);
      return;
    }

    // Final invoice flow
    if (docType === "final") {
      const res = await rpc<{ id?: number }>("invoicing.create_final", {
        project_id: projectId,
        invoice_date: invoiceDate,
      });
      if (res.ok) { await onCreated(res.data?.id, res.warning); }
      else { setError(res.error || "Failed to create final invoice"); }
      setSubmitting(false);
      return;
    }

    // Standard invoice flow
    const params: Record<string, unknown> = {
      project_id: projectId,
      invoice_date: invoiceDate,
      from_date: fromDate,
      to_date: toDate,
    };
    if (isFixedPrice) {
      // fixed-price: backend handles everything from the contract
    } else if (mode === "manual") {
      if (!itemsValid()) { setError("Fill in all line items with valid values"); setSubmitting(false); return; }
      params.manual_items = lineItems.map((it) => ({
        description: it.description.trim(),
        quantity: parseFloat(it.quantity),
        unit: it.unit,
        unit_price: parseFloat(it.unitPrice),
      }));
    } else {
      params.with_timesheet = withTimesheet;
    }
    const custom = customNoteText.trim();
    if (custom) await rpc("invoice_notes.create", { text: custom });
    const parts: string[] = [];
    for (const n of savedNotes) {
      if (selectedNoteIds.has(n.id)) parts.push(str(n, "text"));
    }
    if (custom) parts.push(custom);
    if (parts.length > 0) params.notes = parts.join("\n");
    const res = await rpc<{ id?: number }>("invoicing.create", params);
    if (res.ok) {
      await onCreated(res.data?.id, res.warning);
    } else {
      setError(res.error || "Failed to create invoice");
    }
    setSubmitting(false);
  }

  return (
    <Dialog onClose={onClose} width="w-[560px]">
      <DialogHeader className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Create Invoice</h2>
        <StepDots steps={CREATE_INVOICE_STEPS} current={step} />
      </DialogHeader>
      {/* min-h: same size on both steps, and room for the contract tooltip */}
      <DialogBody className="min-h-84 px-5 py-4 space-y-4">
        <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>
        {/* Step 1: project, document type and source */}
        {step === 0 && (
          <div data-tour="invoice-project">
            <label className="block">
              <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Project<span className="text-accent ml-0.5">*</span></span>
              <select value={projectId ?? ""} onChange={(e) => handleProjectChange(Number(e.target.value))}
                className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary">
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{str(p, "title")}</option>
                ))}
              </select>
            </label>
            {selectedContract && <ContractPreview contract={selectedContract} />}
          </div>
        )}

        {/* Document type (only when contract has milestones) */}
        {step === 0 && hasMilestones && isFixedPrice && (
          <div>
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Document Type</span>
            <div className="flex gap-2 mt-1">
              {DOCUMENT_TYPE_OPTIONS.map(({ value, label, icon: Icon }) => {
                // Settling early is only meaningful once a deposit exists to deduct.
                const disabled = value === "final" && !canSettle;
                const disabledReason = isSettled
                  ? "A final invoice already settles this project"
                  : "Invoice at least one milestone first";
                return (
                  <button key={value} type="button" disabled={disabled}
                    onClick={() => { setDocType(value); setSelectedMilestoneId(null); }}
                    title={disabled ? disabledReason : undefined}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-colors border
                      ${docType === value ? "border-accent bg-accent/15 text-primary" : "border-border-subtle text-tertiary"}
                      ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}>
                    <Icon size={14} /> {label}
                  </button>
                );
              })}
            </div>
            {docType === "final" && (
              <p className="text-[10px] text-status-info mt-1">
                States the full contract amount and deducts every deposit already issued.
              </p>
            )}
          </div>
        )}

        {/* Milestone picker (deposit only) */}
        {step === 0 && docType === "deposit" && hasMilestones && (
          <label className="block">
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Milestone</span>
            <select value={selectedMilestoneId ?? ""} onChange={(e) => setSelectedMilestoneId(e.target.value ? Number(e.target.value) : null)}
              className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary">
              <option value="">— Select milestone —</option>
              {openMilestones.map((m) => (
                <option key={m.id} value={m.id}>
                  {str(m, "title")} ({num(m, "percentage")}%)
                  {openMilestones.length === 1 ? " — final settlement" : ""}
                </option>
              ))}
            </select>
            {isLastOpenMilestone && (
              <p className="text-[10px] text-status-info mt-1">
                Last milestone — creates the final settlement invoice with prior deposits deducted.
              </p>
            )}
            {openMilestones.length === 0 && (
              <p className="text-[10px] text-muted mt-1">All milestones have been invoiced.</p>
            )}
          </label>
        )}

        {/* Additional charges the contract will add on top — only when it has any */}
        {step === 0 && mode !== "manual" && charges.length > 0 && (
          <div className="px-3 py-2.5 rounded-lg bg-bg-card border border-border-subtle">
            <div className="text-[10px] font-semibold text-muted uppercase tracking-wider">Additional charges</div>
            <div className="mt-1.5 space-y-1">
              {charges.map((charge) => (
                <div key={charge.id} className="flex items-center justify-between gap-2 text-xs">
                  <span className="text-secondary truncate">
                    {str(charge, "description")}
                    <span className="text-muted ml-1.5">
                      {CHARGE_BASIS_LABELS[str(charge, "basis")] || str(charge, "basis")}
                    </span>
                  </span>
                  <span className="text-primary tabular-nums shrink-0">
                    {num(charge, "amount")} {chargeCurrency}
                  </span>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-muted mt-1.5">Added to this invoice as separate lines.</p>
          </div>
        )}

        {/* Mode toggle (time-based only, not for deposit/final) */}
        {step === 0 && !isFixedPrice && docType === "invoice" && (
          <div data-tour="invoice-source">
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Source</span>
            <div className="flex gap-2 mt-1">
              <button onClick={() => setMode("timetracking")} disabled={!hasTimeData}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-colors border
                  ${mode === "timetracking" ? "border-accent bg-accent/15 text-primary" : "border-border-subtle text-tertiary"}
                  ${!hasTimeData ? "opacity-40 cursor-not-allowed" : ""}`}>
                <Clock size={14} /> Time Tracking
              </button>
              <button onClick={() => setMode("manual")}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-colors border
                  ${mode === "manual" ? "border-accent bg-accent/15 text-primary" : "border-border-subtle text-tertiary"}`}>
                <FileText size={14} /> Manual
              </button>
            </div>
            {!hasTimeData && (
              <p className="text-[10px] text-muted mt-1">No tracked time yet.</p>
            )}
          </div>
        )}

        {/* Timesheet opt-out (time-tracking mode only, not for deposit/final) */}
        {step === 0 && !isFixedPrice && mode === "timetracking" && docType === "invoice" && (
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={withTimesheet}
                onChange={(e) => setWithTimesheet(e.target.checked)}
                className="accent-accent" />
              <span className="text-sm text-primary">Generate timesheet PDF</span>
            </label>
          </div>
        )}

        {/* Step 2: dates, line items and notes */}
        {step === 1 && (
          <div className="space-y-2">
            <label className="block">
              <span className="text-[10px] font-semibold text-muted uppercase">Invoice Date<span className="text-accent ml-0.5">*</span></span>
              <input type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)}
                className="mt-1 w-full px-2 py-1.5 rounded-md bg-bg-card border border-border-subtle text-xs text-primary" />
            </label>
            {!isFixedPrice && docType === "invoice" && (
              <div>
                <span className="text-[10px] font-semibold text-muted uppercase">Billing Period<span className="text-accent ml-0.5">*</span></span>
                <div className="mt-1 flex items-center gap-2">
                  <button type="button" onClick={() => shiftMonth(-1)}
                    className="p-1 rounded hover:bg-bg-hover text-secondary transition-colors" title="Previous month">
                    <ChevronLeft size={14} />
                  </button>
                  <label className="block flex-1">
                    <span className="text-[10px] font-semibold text-muted uppercase">From</span>
                    <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
                      className="mt-0.5 w-full px-2 py-1.5 rounded-md bg-bg-card border border-border-subtle text-xs text-primary" />
                  </label>
                  <span className="text-muted text-xs pt-3">–</span>
                  <label className="block flex-1">
                    <span className="text-[10px] font-semibold text-muted uppercase">To</span>
                    <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
                      className="mt-0.5 w-full px-2 py-1.5 rounded-md bg-bg-card border border-border-subtle text-xs text-primary" />
                  </label>
                  <button type="button" onClick={() => shiftMonth(1)}
                    className="p-1 rounded hover:bg-bg-hover text-secondary transition-colors" title="Next month">
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Line items editor (time-based manual only, not for deposit/final) */}
        {step === 1 && !isFixedPrice && mode === "manual" && docType === "invoice" && (
          <div>
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Line Items</span>
            <div className="mt-1 space-y-2">
              {lineItems.map((item, idx) => (
                <div key={idx} className="flex gap-1.5 items-start p-2 rounded-lg bg-bg-card border border-border-subtle">
                  <div className="flex-1 min-w-0 space-y-1.5">
                    <input type="text" placeholder="Description" value={item.description}
                      onChange={(e) => updateItem(idx, { description: e.target.value })}
                      className="w-full px-2 py-1 rounded bg-bg-content border border-border-subtle text-xs text-primary placeholder:text-muted" />
                    <div className="flex gap-1.5">
                      <input type="number" min="0" step="0.5" placeholder="Qty" value={item.quantity}
                        onChange={(e) => updateItem(idx, { quantity: e.target.value })}
                        className="w-20 px-2 py-1 rounded bg-bg-content border border-border-subtle text-xs text-primary placeholder:text-muted tabular-nums" />
                      <select value={item.unit} onChange={(e) => updateItem(idx, { unit: e.target.value })}
                        className="w-20 px-1.5 py-1 rounded bg-bg-content border border-border-subtle text-xs text-primary">
                        {UNIT_OPTIONS.map((u) => <option key={u} value={u}>{u}</option>)}
                      </select>
                      <div className="flex items-center gap-0.5 flex-1 min-w-0">
                        <span className="text-xs text-muted">@</span>
                        <input type="number" min="0" step="0.01" placeholder="Unit price" value={item.unitPrice}
                          onChange={(e) => updateItem(idx, { unitPrice: e.target.value })}
                          className="flex-1 min-w-0 px-2 py-1 rounded bg-bg-content border border-border-subtle text-xs text-primary placeholder:text-muted tabular-nums" />
                      </div>
                    </div>
                  </div>
                  {lineItems.length > 1 && (
                    <button onClick={() => removeItem(idx)} className="mt-1 p-1 rounded text-muted hover:text-status-danger hover:bg-status-danger/10 transition-colors"
                      title="Remove item">
                      <XCircle size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button onClick={addItem}
              className="mt-2 flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors">
              <Plus size={12} /> Add item
            </button>
          </div>
        )}

        {/* Notes */}
        {step === 1 && (
          <div>
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Closing Notes</span>
            <p className="text-[10px] text-muted mt-0.5 mb-1.5">Optional text printed at the bottom of the invoice (e.g. VAT exemption, reverse charge).</p>
            {savedNotes.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {savedNotes.map((n) => {
                  const active = selectedNoteIds.has(n.id);
                  return (
                    <button key={n.id} type="button"
                      onClick={() => setSelectedNoteIds((prev) => {
                        const next = new Set(prev);
                        if (active) next.delete(n.id); else next.add(n.id);
                        return next;
                      })}
                      className={`px-2.5 py-1 rounded-full text-[11px] leading-tight border transition-colors truncate max-w-[280px]
                        ${active
                          ? "border-accent bg-accent/15 text-primary"
                          : "border-border-subtle text-secondary hover:border-accent/50 hover:text-primary"}`}
                      title={str(n, "text")}
                    >
                      {str(n, "text")}
                    </button>
                  );
                })}
              </div>
            )}
            <textarea
              value={customNoteText}
              onChange={(e) => setCustomNoteText(e.target.value)}
              placeholder="Type additional notes…"
              rows={2}
              className="w-full px-2.5 py-1.5 rounded-md bg-bg-card border border-border-subtle text-xs text-primary placeholder:text-muted resize-y"
            />
          </div>
        )}

        {error && <p className="text-xs text-status-danger">{error}</p>}
      </DialogBody>

      <DialogFooter className="flex items-center gap-2">
        {step === 1 && (
          <button onClick={() => setStep(0)}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
            <ChevronLeft size={14} /> Back
          </button>
        )}
        <button onClick={onClose}
          className="ml-auto px-4 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
          Cancel
        </button>
        {step === 0 ? (
          <button onClick={() => setStep(1)} disabled={!canAdvance}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium bg-accent text-on-fill hover:bg-accent/90 transition-colors disabled:opacity-50">
            Next <ChevronRight size={14} />
          </button>
        ) : (
          <button onClick={submit} disabled={submitting}
            className="px-4 py-1.5 rounded-md text-sm font-medium bg-accent text-on-fill hover:bg-accent/90 transition-colors disabled:opacity-50">
            {submitting ? "Creating…"
              : docType === "final" ? "Create Final Invoice"
              : docType === "deposit" ? (isLastOpenMilestone ? "Create Final Invoice" : "Create Deposit Invoice")
              : "Create Invoice"}
          </button>
        )}
      </DialogFooter>
    </Dialog>
  );
}
