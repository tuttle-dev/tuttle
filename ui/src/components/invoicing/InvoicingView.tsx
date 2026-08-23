import { useEffect, useState, useCallback, useMemo } from "react";
import {
  FileText, Send, CheckCircle, XCircle, Mail, Trash2,
  Building2, FolderKanban, Calendar, Banknote, Eye, DollarSign,
  Plus, Clock, AlertTriangle, ChevronLeft, ChevronRight, Search, Share, Receipt, Milestone,
} from "lucide-react";
import { rpc, readFileAsDataURL } from "../../api/rpc";
import { str, num, bool, entity as subEntity, list as entityList, formatDate, invoiceStatus, deepStr, isReminder, isDeposit, isFinalInvoice, reminderLevel, depositChainHeadId, depositMilestoneLabel, milestoneScheduleStatus, type MilestoneScheduleStatus } from "../../api/entity";
import { taxCategory, taxTreatment } from "../../api/tax";
import { StatusBadge } from "../shared/StatusBadge";
import { ViewModeToggle } from "../shared/ViewModeToggle";
import { KanbanBoard, useStageStore, type BoardColumn } from "../shared/KanbanBoard";
import { Toolbar, ToolbarButtonPrimary, ToolbarFilterGroup, ListDetailLayout, LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import { useNavigation } from "../shared/NavigationContext";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import type { Entity } from "../../api/types";

type InvoiceChain = { root: Entity; reminders: Entity[]; deposits: Entity[] };

const INVOICE_COLUMNS: BoardColumn[] = [
  { id: "Draft", label: "Draft", color: "#8e8e93" },
  { id: "Sent", label: "Sent", color: "#3b82f6" },
  { id: "Overdue", label: "Overdue", color: "#ef4444" },
  { id: "Paid", label: "Paid", color: "#22c55e" },
  { id: "Cancelled", label: "Cancelled", color: "#f97316" },
];

const STATUS_FILTERS = ["All", "Draft", "Sent", "Paid", "Overdue", "Cancelled"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const FILTER_COLORS: Record<string, string> = {
  All: "#007AFF", Draft: "#a0a0a0", Sent: "#60a5fa",
  Paid: "#34d399", Overdue: "#f87171", Cancelled: "#fb923c",
};

type DocumentType = "invoice" | "deposit" | "final";

const DOCUMENT_TYPE_OPTIONS = [
  { value: "invoice" as DocumentType, label: "Invoice", icon: FileText },
  { value: "deposit" as DocumentType, label: "Deposit", icon: Milestone },
  { value: "final" as DocumentType, label: "Final", icon: Receipt },
];

export function InvoicingView() {
  const { filter: navFilter } = useNavigation();
  const [invoices, setInvoices] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"list" | "board">("list");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [newlyCreatedId, setNewlyCreatedId] = useState<number | null>(null);
  const [mailError, setMailError] = useState<string | null>(null);
  const [renderWarning, setRenderWarning] = useState<string | null>(null);

  const defaultColumn = useCallback(
    (e: { id: number; [k: string]: unknown }) => invoiceStatus(e as Entity), [],
  );
  const stageStore = useStageStore("invoice", INVOICE_COLUMNS, defaultColumn);

  useEffect(() => { load(); }, []);
  useEffect(() => { setMailError(null); }, [selected?.id]);
  useEffect(() => {
    if (selected && !filtered.some((inv) => inv.id === selected.id)) setSelected(null);
  }, [statusFilter, search, invoices]); // eslint-disable-line react-hooks/exhaustive-deps

  async function load(selectId?: number) {
    setLoading(true);
    const res = await rpc<Entity[]>("invoicing.get_all");
    if (res.ok && res.data) {
      const sorted = [...res.data].sort((a, b) => {
        const na = str(a, "number") || "";
        const nb = str(b, "number") || "";
        return nb.localeCompare(na);
      });
      setInvoices(sorted);
      const refreshId = selectId ?? selected?.id;
      if (refreshId != null) {
        const match = res.data.find((i) => i.id === refreshId);
        setSelected(match ?? null);
      }
    }
    setLoading(false);
  }

  function matchesSearch(inv: Entity) {
    if (!search) return true;
    const q = search.toLowerCase();
    return str(inv, "number").toLowerCase().includes(q)
      || deepStr(inv, "contract.client.name").toLowerCase().includes(q)
      || deepStr(inv, "project.title").toLowerCase().includes(q);
  }

  const filtered = invoices.filter((inv) =>
    (statusFilter === "All" || invoiceStatus(inv) === statusFilter) && matchesSearch(inv));
  const boardFiltered = invoices.filter(matchesSearch);

  const chains = useMemo(() => buildChains(filtered), [filtered]);
  const boardChains = useMemo(() => buildChains(boardFiltered), [boardFiltered]);
  const boardRoots = useMemo(() => boardChains.map((c) => c.root), [boardChains]);
  const reminderCountMap = useMemo(() => {
    const m = new Map<number, number>();
    for (const c of boardChains) m.set(c.root.id, c.reminders.length);
    return m;
  }, [boardChains]);
  const depositCountMap = useMemo(() => {
    const m = new Map<number, number>();
    for (const c of boardChains) {
      if (c.deposits.length > 0) m.set(c.root.id, c.deposits.length);
    }
    return m;
  }, [boardChains]);
  const chainByRootId = useMemo(() => {
    const m = new Map<number, InvoiceChain>();
    for (const c of boardChains) m.set(c.root.id, c);
    return m;
  }, [boardChains]);

  async function toggleSent(id: number) { await rpc("invoicing.toggle_sent", { id }); load(); }
  async function togglePaid(id: number) { await rpc("invoicing.toggle_paid", { id }); load(); }
  async function toggleCancelled(id: number) { await rpc("invoicing.toggle_cancelled", { id }); load(); }
  async function sendMail(id: number) {
    setMailError(null);
    const res = await rpc<void>("invoicing.send_mail", { id });
    if (!res.ok) setMailError(res.error || "Failed to send invoice");
  }
  const [deleteError, setDeleteError] = useState<string | null>(null);
  async function handleDelete(id: number) {
    setDeleteError(null);
    const res = await rpc("invoicing.delete", { id });
    if (res.ok) { setSelected(null); load(); }
    else setDeleteError(res.error || "Failed to delete invoice.");
  }

  async function moveToColumn(id: number, colId: string) {
    const inv = invoices.find((i) => i.id === id);
    if (!inv) return;
    if (stageStore.columnFor(inv) === colId) return;
    stageStore.setColumn(id, colId);
    const isSent = bool(inv, "sent"), isPaid = bool(inv, "paid"), isCancelled = bool(inv, "cancelled");
    if (colId === "Draft") { if (isSent) await toggleSent(id); if (isPaid) await togglePaid(id); if (isCancelled) await toggleCancelled(id); }
    else if (colId === "Sent") { if (isCancelled) await toggleCancelled(id); if (isPaid) await togglePaid(id); if (!isSent) await toggleSent(id); }
    else if (colId === "Paid") { if (isCancelled) await toggleCancelled(id); if (!isSent) await toggleSent(id); if (!isPaid) await togglePaid(id); }
    else if (colId === "Overdue") { if (isCancelled) await toggleCancelled(id); if (!isSent) await toggleSent(id); if (isPaid) await togglePaid(id); }
    else if (colId === "Cancelled") { if (!isCancelled) await toggleCancelled(id); }
    load();
  }

  if (loading && invoices.length === 0)
    return <div className="flex items-center justify-center h-full text-secondary">Loading invoices…</div>;

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Invoicing"
        actions={viewMode === "list"
          ? <ToolbarButtonPrimary icon={<Plus size={13} />} label="Create Invoice" onClick={() => setCreateOpen(true)} />
          : undefined}
        center={viewMode === "list"
          ? <ToolbarFilterGroup options={STATUS_FILTERS} value={statusFilter} onChange={setStatusFilter} colors={FILTER_COLORS} />
          : undefined}
        right={<ViewModeToggle mode={viewMode} onChange={setViewMode} />}
        search={{ value: search, onChange: setSearch }}
      />

      {renderWarning && (
        <div className="mx-4 mt-2 flex items-center gap-2 px-3 py-2 rounded-md text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30">
          <AlertTriangle size={14} className="shrink-0" />
          <span className="flex-1">{renderWarning}</span>
          <button onClick={() => setRenderWarning(null)} className="text-amber-300 hover:text-amber-200">✕</button>
        </div>
      )}

      {invoices.length === 0 ? (
        <EmptyStateIntro icon={FileText} description="Invoices are how you bill clients for completed work. Create, track, and send them from here." />
      ) : viewMode === "list" ? (
        <ListDetailLayout
          footer={<>{filtered.length} invoice{filtered.length !== 1 ? "s" : ""}</>}
          list={chains.length === 0
            ? <div className="p-4 text-sm text-center text-tertiary">No matches.</div>
            : chains.map((chain) => {
              const inv = chain.root;
              const isSelected = selected?.id === inv.id;
              const isHighlighted = !isSelected && (inv.id === newlyCreatedId || (navFilter.contractId != null && num(inv, "contract_id") === navFilter.contractId));
              return (
                <div key={inv.id} className={chainAccentClass(chain)}>
                  <InvoiceRow invoice={inv} isSelected={isSelected} isHighlighted={isHighlighted}
                    reminderCount={chain.reminders.length}
                    depositCount={chain.deposits.length}
                    schedule={milestoneScheduleStatus(inv, chain.deposits)}
                    onSelect={() => { setNewlyCreatedId(null); setSelected(inv); }} />
                  {chain.deposits.map((dep) => {
                    const depSelected = selected?.id === dep.id;
                    return <DepositRow key={dep.id} invoice={dep} isSelected={depSelected}
                      onSelect={() => { setNewlyCreatedId(null); setSelected(dep); }} />;
                  })}
                  {chain.reminders.map((rem) => {
                    const remSelected = selected?.id === rem.id;
                    return <ReminderRow key={rem.id} invoice={rem} isSelected={remSelected}
                      onSelect={() => { setNewlyCreatedId(null); setSelected(rem); }} />;
                  })}
                </div>
              );
            })
          }
          detail={selected ? (
              <InvoiceDetail invoice={selected} allInvoices={invoices}
                onToggleSent={() => toggleSent(selected.id)}
                onTogglePaid={() => togglePaid(selected.id)} onToggleCancelled={() => toggleCancelled(selected.id)}
                onSendMail={() => sendMail(selected.id)}
                onDelete={() => handleDelete(selected.id)} deleteError={deleteError}
                mailError={mailError} onClearMailError={() => setMailError(null)}
                onReminderCreated={(newId, warning) => { setRenderWarning(warning ?? null); load(newId); }}
                onRefresh={() => load(selected.id)} />
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-tertiary">
                <FileText size={36} strokeWidth={1.2} /><span className="text-sm">Select an invoice</span>
              </div>
            )
          }
        />
      ) : (
        <div className="flex-1 overflow-hidden">
          <KanbanBoard entities={boardRoots} columns={INVOICE_COLUMNS}
            columnFor={(e) => stageStore.columnFor(e)} onMove={moveToColumn}
            renderCard={(inv, col) => (
              <InvoiceChainCard
                chain={chainByRootId.get(inv.id) ?? { root: inv, reminders: [], deposits: [] }}
                color={col.color}
                reminderCount={reminderCountMap.get(inv.id) || 0}
                depositCount={depositCountMap.get(inv.id) || 0}
              />
            )} />
        </div>
      )}

      {createOpen && (
        <CreateInvoiceDialog
          onClose={() => setCreateOpen(false)}
          onCreated={async (newId, warning) => {
            setNewlyCreatedId(newId ?? null);
            setRenderWarning(warning ?? null);
            await load(newId);
            setCreateOpen(false);
          }}
        />
      )}
    </div>
  );
}

interface LineItem {
  description: string;
  quantity: string;
  unit: string;
  unitPrice: string;
}

const UNIT_OPTIONS = ["hour", "day", "piece", "flat"] as const;

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

function CreateInvoiceDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (newId?: number, warning?: string | null) => Promise<void> | void }) {
  const [projects, setProjects] = useState<Entity[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10));
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
  const canSettle = hasMilestones && openMilestones.length < milestones.length;

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
        if (active.length > 0) {
          setProjectId(active[0].id);
          setLineItems(makeDefaultItems(active[0]));
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

  function itemsValid(): boolean {
    return lineItems.every((it) => {
      const qty = parseFloat(it.quantity);
      const price = parseFloat(it.unitPrice);
      return it.description.trim() && qty > 0 && price >= 0;
    });
  }

  async function submit() {
    if (!projectId) { setError("Select a project"); return; }
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-bg-content rounded-xl border border-border-subtle shadow-2xl w-[560px] max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}>
        <div className="px-5 py-4 border-b border-border-subtle">
          <h2 className="text-base font-semibold">Create Invoice</h2>
        </div>
        <div className="px-5 py-4 space-y-4">
          <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>
          {/* Project */}
          <label className="block">
            <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Project<span className="text-accent ml-0.5">*</span></span>
            <select value={projectId ?? ""} onChange={(e) => handleProjectChange(Number(e.target.value))}
              className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary">
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{str(p, "title")}</option>
              ))}
            </select>
          </label>

          {/* Document type (only when contract has milestones) */}
          {hasMilestones && isFixedPrice && (
            <div>
              <span className="text-xs font-semibold text-secondary uppercase tracking-wider">Document Type</span>
              <div className="flex gap-2 mt-1">
                {DOCUMENT_TYPE_OPTIONS.map(({ value, label, icon: Icon }) => {
                  // Settling early is only meaningful once a deposit exists to deduct.
                  const disabled = value === "final" && !canSettle;
                  return (
                    <button key={value} type="button" disabled={disabled}
                      onClick={() => { setDocType(value); setSelectedMilestoneId(null); }}
                      title={disabled ? "Invoice at least one milestone first" : undefined}
                      className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-colors border
                        ${docType === value ? "border-accent bg-accent/15 text-primary" : "border-border-subtle text-tertiary"}
                        ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}>
                      <Icon size={14} /> {label}
                    </button>
                  );
                })}
              </div>
              {docType === "final" && (
                <p className="text-[10px] text-blue-300 mt-1">
                  States the full contract amount and deducts every deposit already issued.
                </p>
              )}
            </div>
          )}

          {/* Milestone picker (deposit only) */}
          {docType === "deposit" && hasMilestones && (
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
                <p className="text-[10px] text-blue-300 mt-1">
                  Last milestone — creates the final settlement invoice with prior deposits deducted.
                </p>
              )}
              {openMilestones.length === 0 && (
                <p className="text-[10px] text-muted mt-1">All milestones have been invoiced.</p>
              )}
            </label>
          )}

          {/* Fixed-price notice */}
          {isFixedPrice && docType === "invoice" && selectedProject && (() => {
            const ct = subEntity(selectedProject, "contract");
            const price = ct ? num(ct, "fixed_price") : 0;
            const currency = ct ? str(ct, "currency") : "EUR";
            return (
              <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-accent/10 border border-accent/20">
                <DollarSign size={14} className="text-accent shrink-0" />
                <span className="text-xs text-primary">
                  Fixed price contract — <span className="font-medium">{price} {currency}</span>
                </span>
              </div>
            );
          })()}

          {/* Additional charges the contract will add on top — only when it has any */}
          {mode !== "manual" && charges.length > 0 && (
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
          {!isFixedPrice && docType === "invoice" && (
            <div>
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
                <p className="text-[10px] text-muted mt-1">Import calendar data in Time Tracking to use this option.</p>
              )}
            </div>
          )}

          {/* Timesheet opt-out (time-tracking mode only, not for deposit/final) */}
          {!isFixedPrice && mode === "timetracking" && docType === "invoice" && (
            <div>
              <label className="flex items-start gap-2 cursor-pointer">
                <input type="checkbox" checked={withTimesheet}
                  onChange={(e) => setWithTimesheet(e.target.checked)}
                  className="mt-0.5 accent-accent" />
                <div className="flex-1">
                  <div className="text-sm text-primary">Generate timesheet PDF</div>
                  <div className="text-[10px] text-muted">
                    You can also generate it later from the invoice view.
                  </div>
                </div>
              </label>
            </div>
          )}

          {/* Dates */}
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

          {/* Line items editor (time-based manual only, not for deposit/final) */}
          {!isFixedPrice && mode === "manual" && docType === "invoice" && (
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
                      <button onClick={() => removeItem(idx)} className="mt-1 p-1 rounded text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
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

          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>

        <div className="px-5 py-3 border-t border-border-subtle flex justify-end gap-2">
          <button onClick={onClose}
            className="px-4 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
            Cancel
          </button>
          <button onClick={submit} disabled={submitting}
            className="px-4 py-1.5 rounded-md text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-50">
            {submitting ? "Creating…"
              : docType === "final" ? "Create Final Invoice"
              : docType === "deposit" ? (isLastOpenMilestone ? "Create Final Invoice" : "Create Deposit Invoice")
              : "Create Invoice"}
          </button>
        </div>
      </div>
    </div>
  );
}

function DocumentTypeBadge({ type }: { type: "deposit" | "final" }) {
  if (type === "deposit") {
    return (
      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/15 text-blue-400 shrink-0">
        Deposit
      </span>
    );
  }
  return (
    <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-300 shrink-0">
      Final
    </span>
  );
}

function chainAccentClass(chain: InvoiceChain): string {
  if (isFinalInvoice(chain.root) || isDeposit(chain.root) || chain.deposits.length > 0) {
    return "border-l-2 border-l-blue-400";
  }
  return "";
}

function MilestoneScheduleBadge({ schedule }: { schedule: MilestoneScheduleStatus }) {
  const { total, invoicedCount, issuedCount, paidCount, hasFinal, settled } = schedule;

  if (settled) {
    return (
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-green-500/10 text-green-400 shrink-0">
        All settled
      </span>
    );
  }
  if (hasFinal) {
    return (
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 shrink-0">
        Settlement · {paidCount}/{issuedCount} paid
      </span>
    );
  }
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 ${
      invoicedCount === total ? "bg-blue-500/10 text-blue-400" : "bg-amber-500/10 text-amber-400"
    }`}>
      {invoicedCount}/{total} milestones invoiced · {paidCount}/{issuedCount} paid
    </span>
  );
}

function InvoiceRow({ invoice, isSelected, isHighlighted, reminderCount, depositCount, schedule, onSelect }: {
  invoice: Entity; isSelected: boolean; isHighlighted?: boolean;
  reminderCount?: number; depositCount?: number; schedule?: MilestoneScheduleStatus | null; onSelect: () => void;
}) {
  const status = invoiceStatus(invoice);
  const depositLabel = depositMilestoneLabel(invoice);
  const isFinal = isFinalInvoice(invoice);
  return (
    <button onClick={onSelect}
      className={`w-full text-left ${LIST_ROW_PADDING} border-b transition-colors
        ${isSelected ? "bg-bg-selected border-border-subtle" : isHighlighted ? "bg-accent/10 border-accent/30" : "border-border-subtle hover:bg-bg-hover"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium shrink-0">{str(invoice, "number") || "Draft"}</span>
          {isDeposit(invoice) && depositLabel && (
            <span className="text-xs font-semibold text-blue-400 truncate">{depositLabel}</span>
          )}
          {isFinal && (
            <span className="text-xs font-semibold text-blue-300 truncate">Settlement</span>
          )}
          <span className="text-xs text-tertiary shrink-0">{formatDate(str(invoice, "date"))}</span>
          {isDeposit(invoice) && <DocumentTypeBadge type="deposit" />}
          {isFinal && <DocumentTypeBadge type="final" />}
          {(depositCount ?? 0) > 0 && !isDeposit(invoice) && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/15 text-blue-400">
              <Milestone size={10} />{depositCount}
            </span>
          )}
          {(reminderCount ?? 0) > 0 && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-600">
              <AlertTriangle size={10} />{reminderCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <span className="text-sm font-semibold tabular-nums">{str(invoice, "total_formatted")}</span>
          <StatusBadge status={status} />
        </div>
      </div>
      <div className="flex items-center gap-1.5 mt-1 flex-wrap text-secondary">
        <span className="text-xs truncate">{deepStr(invoice, "contract.client.name") || "No client"}</span>
        {deepStr(invoice, "project.title") && (
          <><span className="text-tertiary">·</span>
          <span className="text-xs text-tertiary truncate">{deepStr(invoice, "project.title")}</span></>
        )}
        {schedule && <MilestoneScheduleBadge schedule={schedule} />}
      </div>
    </button>
  );
}

function ReminderRow({ invoice, isSelected, onSelect }: { invoice: Entity; isSelected: boolean; onSelect: () => void }) {
  const status = invoiceStatus(invoice);
  const level = reminderLevel(invoice);
  return (
    <button onClick={onSelect}
      className={`w-full text-left pl-10 pr-4 py-2.5 border-b transition-colors border-l-2 border-l-amber-400
        ${isSelected ? "bg-bg-selected border-b-border-subtle" : "border-b-border-subtle hover:bg-bg-hover bg-bg-content/50"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-semibold text-amber-600">Reminder {level}</span>
          <span className="text-xs text-tertiary">{formatDate(str(invoice, "date"))}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <span className="text-xs font-semibold tabular-nums">{str(invoice, "total_formatted")}</span>
          <StatusBadge status={status} />
        </div>
      </div>
    </button>
  );
}

function DepositRow({ invoice, isSelected, onSelect }: { invoice: Entity; isSelected: boolean; onSelect: () => void }) {
  const status = invoiceStatus(invoice);
  const depositLabel = depositMilestoneLabel(invoice);
  return (
    <button onClick={onSelect}
      className={`w-full text-left pl-10 pr-4 py-2.5 border-b transition-colors border-l-2 border-l-blue-400
        ${isSelected ? "bg-bg-selected border-b-border-subtle" : "border-b-border-subtle hover:bg-bg-hover bg-bg-content/50"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-semibold text-blue-400 truncate">
            {depositLabel || "Deposit"}
          </span>
          <DocumentTypeBadge type="deposit" />
          <span className="text-xs text-tertiary shrink-0">{str(invoice, "number")}</span>
          <span className="text-xs text-tertiary shrink-0">{formatDate(str(invoice, "date"))}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <span className="text-xs font-semibold tabular-nums">{str(invoice, "total_formatted")}</span>
          <StatusBadge status={status} />
        </div>
      </div>
    </button>
  );
}

function InvoiceChainCard({ chain, color, reminderCount, depositCount }: {
  chain: InvoiceChain; color: string; reminderCount?: number; depositCount?: number;
}) {
  const { root, deposits } = chain;
  const schedule = milestoneScheduleStatus(root, deposits);
  return (
    <div className="space-y-1.5">
      <InvoiceCard invoice={root} color={color} reminderCount={reminderCount} depositCount={depositCount} schedule={schedule} />
      {deposits.length > 0 && (
        <div className="ml-2 pl-2 border-l-2 border-blue-400/60 space-y-1.5">
          {deposits.map((dep) => (
            <div key={dep.id} className="pt-1 border-t border-border-subtle/60 first:border-t-0 first:pt-0">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1 min-w-0">
                  <span className="text-xs font-semibold text-blue-400 truncate">
                    {depositMilestoneLabel(dep) || "Deposit"}
                  </span>
                  <DocumentTypeBadge type="deposit" />
                  <span className="text-[10px] text-tertiary truncate">{str(dep, "number") || "Draft"}</span>
                </div>
                <span className="text-xs font-semibold tabular-nums shrink-0">{str(dep, "total_formatted")}</span>
              </div>
              <div className="text-[10px] text-tertiary mt-0.5">{formatDate(str(dep, "date"))}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function InvoiceCard({ invoice, reminderCount, depositCount, schedule }: { invoice: Entity; color: string; reminderCount?: number; depositCount?: number; schedule?: MilestoneScheduleStatus | null }) {
  const depositLabel = depositMilestoneLabel(invoice);
  const isFinal = isFinalInvoice(invoice);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-sm font-semibold shrink-0">{str(invoice, "number") || "Draft"}</span>
          {isDeposit(invoice) && depositLabel && (
            <span className="text-xs font-semibold text-blue-400 truncate">{depositLabel}</span>
          )}
          {isFinal && (
            <span className="text-xs font-semibold text-blue-300 truncate">Settlement</span>
          )}
          {isDeposit(invoice) && <DocumentTypeBadge type="deposit" />}
          {isFinal && <DocumentTypeBadge type="final" />}
          {(depositCount ?? 0) > 0 && !isDeposit(invoice) && (
            <span className="flex items-center gap-0.5 px-1 py-0.5 rounded text-[10px] font-semibold bg-blue-500/15 text-blue-400">
              <Milestone size={9} />{depositCount}
            </span>
          )}
          {(reminderCount ?? 0) > 0 && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-600">
              <AlertTriangle size={9} />{reminderCount}
            </span>
          )}
        </div>
        <span className="text-sm font-bold tabular-nums">{str(invoice, "total_formatted")}</span>
      </div>
      {deepStr(invoice, "contract.client.name") && (
        <div className="flex items-center gap-1 text-secondary">
          <Building2 size={12} className="text-tertiary" />
          <span className="text-xs truncate">{deepStr(invoice, "contract.client.name")}</span>
        </div>
      )}
      {deepStr(invoice, "project.title") && (
        <div className="flex items-center gap-1 text-secondary">
          <FolderKanban size={12} className="text-tertiary" />
          <span className="text-xs truncate">{deepStr(invoice, "project.title")}</span>
        </div>
      )}
      <div className="flex items-center gap-1 text-tertiary">
        <Calendar size={12} /><span className="text-xs">{formatDate(str(invoice, "date"))}</span>
      </div>
      {schedule && (
        <div className="pt-0.5">
          <MilestoneScheduleBadge schedule={schedule} />
        </div>
      )}
    </div>
  );
}

function InvoiceDetail({ invoice, allInvoices, onToggleSent, onTogglePaid, onToggleCancelled, onSendMail, onDelete, deleteError, mailError, onClearMailError, onReminderCreated, onRefresh }: {
  invoice: Entity; allInvoices: Entity[];
  onToggleSent: () => void; onTogglePaid: () => void; onToggleCancelled: () => void; onSendMail: () => void;
  onDelete: () => void; deleteError: string | null;
  mailError: string | null; onClearMailError: () => void;
  onReminderCreated: (newId?: number, warning?: string | null) => void;
  onRefresh: () => void;
}) {
  const status = invoiceStatus(invoice);
  const items = entityList(invoice, "items");
  const isCancelled = bool(invoice, "cancelled");
  const isSent = bool(invoice, "sent");
  const isPaid = bool(invoice, "paid");
  const pdfPath = str(invoice, "pdf_path");
  const tsPath = str(invoice, "timesheet_pdf_path");
  const hasTimesheet = bool(invoice, "has_timesheet");
  const isRem = isReminder(invoice);
  const depositLabel = depositMilestoneLabel(invoice);
  const showTimesheetTab = hasTimesheet && !isRem;
  const canCreateReminder = status === "Overdue" && !isCancelled;

  // Line items snapshot the tax category at creation, so they outrank the
  // contract, which may have been edited since. BR-O-11/12 keep them uniform.
  const taxSource = items[0] ?? subEntity(invoice, "contract");
  const invoiceTaxCategory = taxCategory(taxSource ? str(taxSource, "VAT_category") : "S");
  const invoiceVatRate = taxSource ? num(taxSource, "VAT_rate") : 0;

  const chain = useMemo(() => {
    const headId = invoice.reminder_chain_head_id ?? invoice.id;
    const root = allInvoices.find((i) => i.id === headId);
    if (!root) return [];
    const reminders = allInvoices
      .filter((i) => i.reminder_chain_head_id === headId && i.id !== headId)
      .sort((a, b) => num(a, "reminder_level") - num(b, "reminder_level"));
    return [root, ...reminders];
  }, [invoice, allInvoices]);

  const [detailTab, setDetailTab] = useState<"invoice" | "timesheet" | "details">(pdfPath ? "invoice" : "details");
  const [pdfDataUrl, setPdfDataUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [tsPdfDataUrl, setTsPdfDataUrl] = useState<string | null>(null);
  const [tsPdfLoading, setTsPdfLoading] = useState(false);
  const [tsRendering, setTsRendering] = useState(false);
  const [tsError, setTsError] = useState("");
  const [reminderDialogOpen, setReminderDialogOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  useEffect(() => { setDeleteConfirm(false); }, [invoice.id]);

  useEffect(() => {
    setPdfDataUrl(null);
    if (pdfPath) {
      setDetailTab("invoice");
      setPdfLoading(true);
      readFileAsDataURL(pdfPath, "application/pdf").then((url) => {
        setPdfDataUrl(url);
        setPdfLoading(false);
      });
    } else {
      setDetailTab("details");
    }
  }, [pdfPath, invoice.id]);

  useEffect(() => {
    setTsPdfDataUrl(null);
    setTsError("");
    if (tsPath) {
      setTsPdfLoading(true);
      readFileAsDataURL(tsPath, "application/pdf").then((url) => {
        setTsPdfDataUrl(url);
        setTsPdfLoading(false);
      });
    }
  }, [tsPath, invoice.id]);

  async function renderTimesheet() {
    setTsRendering(true);
    setTsError("");
    const res = await rpc("invoicing.render_timesheet_for_invoice", { id: invoice.id });
    setTsRendering(false);
    if (res.ok) {
      onRefresh();
    } else {
      setTsError(res.error || "Failed to render timesheet");
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-5 pb-3 space-y-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-bg-card flex items-center justify-center">
            {isRem
              ? <AlertTriangle size={18} className="text-amber-500" />
              : isFinalInvoice(invoice)
              ? <FileText size={18} className="text-blue-400" />
              : isDeposit(invoice)
              ? <Milestone size={18} className="text-blue-400" />
              : <FileText size={18} className="text-secondary" />}
          </div>
          <div>
            <h1 className="text-lg font-semibold">
              {isRem
                ? `Reminder ${reminderLevel(invoice)}`
                : isDeposit(invoice)
                ? (depositLabel ? `Deposit · ${depositLabel}` : `Deposit ${str(invoice, "number") || "Draft"}`)
                : isFinalInvoice(invoice)
                ? `Final ${str(invoice, "number") || "Draft"}`
                : str(invoice, "number") || "Draft"}
            </h1>
            <div className="flex items-center gap-2 flex-wrap">
              {isDeposit(invoice) && depositLabel && (
                <span className="text-xs text-tertiary">Inv. {str(invoice, "number") || "Draft"}</span>
              )}
              {isFinalInvoice(invoice) && (
                <span className="text-xs font-medium text-blue-300">Settlement invoice</span>
              )}
              <span className="text-sm text-secondary">{deepStr(invoice, "contract.client.name") || "No client"}</span>
              <StatusBadge status={status} />
            </div>
          </div>
        </div>

        {/* A final invoice settles the whole contract: what matters is the
            balance still due after deducting the deposits, not the full total. */}
        <div className="grid grid-cols-3 gap-2">
          {isFinalInvoice(invoice) ? (
            <>
              <AmountCard label="Contract total" value={str(invoice, "total_formatted")} />
              <AmountCard label="Deposits deducted" value={str(invoice, "deposits_deducted_formatted") ? `−${str(invoice, "deposits_deducted_formatted")}` : "—"} color="#3b82f6" />
              <AmountCard label="Balance due" value={str(invoice, "remaining_balance_formatted")} prominent />
            </>
          ) : (
            <>
              <AmountCard label="Subtotal" value={str(invoice, "sum_formatted")} />
              <AmountCard label="VAT" value={invoiceTaxCategory === "O" ? "—" : str(invoice, "vat_total_formatted")} color="#f97316" />
              <AmountCard label="Total" value={str(invoice, "total_formatted")} prominent />
            </>
          )}
        </div>

        {/* Actions group */}
        <Section title="Actions">
          {mailError && (
            <div className="mb-2 flex items-center gap-2 px-3 py-2 rounded-md text-xs text-red-400 bg-red-500/10 border border-red-500/30">
              <span className="flex-1">{mailError}</span>
              <button onClick={onClearMailError} className="text-red-400 hover:text-red-300">✕</button>
            </div>
          )}
          <div className="flex flex-wrap items-center gap-1.5">
            {!isCancelled && !isSent && !isPaid && pdfPath && (
              <button onClick={onSendMail}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-accent text-white hover:bg-accent/90 transition-colors">
                <Mail size={13} /> {isRem ? "Send Reminder" : "Send Invoice"}
              </button>
            )}
            {canCreateReminder && (
              <button onClick={() => setReminderDialogOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-amber-500 text-white hover:bg-amber-500/90 transition-colors">
                <AlertTriangle size={13} /> Create Reminder
              </button>
            )}
            {!isCancelled && pdfPath && (
  <a
    href={pdfDataUrl ?? ""}
    download={(pdfPath.split(/[\\/]/).pop() ?? "invoice.pdf").replace(/[<>:"/\\|?*]+/g, "_")}
    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-sidebar text-secondary border border-border-subtle hover:bg-bg-card hover:text-primary transition-colors"
  >
    <Share size={13} /> Export Invoice
  </a>
)}
{!isCancelled && tsPdfDataUrl && (
  <a
    href={tsPdfDataUrl}
    download={(tsPath.split(/[\\/]/).pop() ?? "timesheet.pdf").replace(/[<>:"/\\|?*]+/g, "_")}
    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-sidebar text-secondary border border-border-subtle hover:bg-bg-card hover:text-primary transition-colors"
  >
    <Share size={13} /> Export Timesheet
  </a>
)}
            <div className="flex-1" />
            {!isCancelled && !isPaid && (
              <ActionBtn label={isSent ? "Sent" : "Mark Sent"} icon={<Send size={13} />}
                color="#3b82f6" active={isSent} onClick={onToggleSent} />
            )}
            {!isCancelled && isSent && (
              <ActionBtn label={isPaid ? "Paid" : "Mark Paid"} icon={<CheckCircle size={13} />}
                color="#22c55e" active={isPaid} onClick={onTogglePaid} />
            )}
            <ActionBtn label={isCancelled ? "Restore" : "Cancel"} icon={<XCircle size={13} />}
              color="#f97316" active={isCancelled} onClick={onToggleCancelled} />
            {!deleteConfirm ? (
              <button onClick={() => setDeleteConfirm(true)}
                className="p-1.5 rounded-md text-secondary hover:text-red-400 border border-border-subtle transition-colors"
                title="Delete invoice">
                <Trash2 size={14} />
              </button>
            ) : (
              <div className="flex items-center gap-1.5 ml-1">
                <span className="text-xs text-red-400">Delete permanently?</span>
                <button onClick={() => { setDeleteConfirm(false); onDelete(); }}
                  className="px-2 py-1 rounded-md text-xs font-medium bg-red-500 text-white hover:bg-red-600 transition-colors">
                  Delete
                </button>
                <button onClick={() => setDeleteConfirm(false)}
                  className="px-2 py-1 rounded-md text-xs font-medium text-secondary hover:text-primary border border-border-subtle transition-colors">
                  Keep
                </button>
              </div>
            )}
          </div>
          {deleteError && (
            <div className="mt-1.5 px-3 py-2 rounded-md text-xs text-red-400 bg-red-500/10 border border-red-500/30">{deleteError}</div>
          )}
        </Section>

        <div className="flex gap-1 border-b border-border-subtle">
          <TabBtn label="Invoice" icon={<Eye size={14} />} active={detailTab === "invoice"}
            disabled={!pdfPath} onClick={() => setDetailTab("invoice")} />
          {showTimesheetTab && (
            <TabBtn label="Timesheet" icon={<Clock size={14} />} active={detailTab === "timesheet"}
              onClick={() => setDetailTab("timesheet")} />
          )}
          <TabBtn label="Details" icon={<FileText size={14} />} active={detailTab === "details"}
            onClick={() => setDetailTab("details")} />
        </div>
      </div>

      {detailTab === "invoice" ? (
        <div className="flex-1 min-h-0 px-5 pb-5">
          {pdfLoading ? (
            <div className="flex items-center justify-center h-full text-secondary">Loading PDF…</div>
         ) : pdfDataUrl ? (
              <embed src={pdfDataUrl} type="application/pdf"
  className="w-full h-full rounded-lg border border-border-subtle" />
          ) : (
            <div className="flex items-center justify-center h-full text-tertiary">
              PDF not available
            </div>
          )}
        </div>
      ) : detailTab === "timesheet" ? (
        <div className="flex-1 min-h-0 px-5 pb-5">
          {tsRendering ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-secondary">
              <Clock size={24} className="animate-pulse" />
              <span className="text-sm">Generating timesheet…</span>
            </div>
          ) : tsPdfLoading ? (
            <div className="flex items-center justify-center h-full text-secondary">Loading PDF…</div>
          ) : tsPdfDataUrl ? (
              <embed src={tsPdfDataUrl} type="application/pdf"
  className="w-full h-full rounded-lg border border-border-subtle" />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-tertiary">
              <FileText size={36} strokeWidth={1.2} />
              <div className="text-sm text-center">No timesheet PDF generated yet.</div>
              <button onClick={renderTimesheet}
                className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors">
                <FileText size={14} /> Generate Timesheet PDF
              </button>
              {tsError && <p className="text-xs text-red-400">{tsError}</p>}
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-5 pb-5 space-y-5">
          {items.length > 0 && (
            <Section title="Line Items">
              <div className="space-y-2">
                {items.map((item, i) => (
                  <div key={i} className="rounded-md p-3 bg-bg-card border border-border-subtle">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{str(item, "description")}</span>
                      <span className="text-sm font-semibold tabular-nums">{str(item, "subtotal_formatted")}</span>
                    </div>
                    <div className="flex items-center gap-3 mt-1.5 text-xs text-secondary">
                      <span>{num(item, "quantity").toFixed(1)} {str(item, "unit") || "hour"}</span>
                      <span>{str(item, "unit_price_formatted")}/{str(item, "unit") || "hour"}</span>
                      <span>{taxTreatment(taxCategory(str(item, "VAT_category")), num(item, "VAT_rate"))}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          <Section title="Details">
            <div className="grid grid-cols-2 gap-3">
              <DRow icon={<Calendar size={14} />} label="Date" value={formatDate(str(invoice, "date"))} />
              <DRow icon={<Calendar size={14} />} label="Due" value={formatDate(str(invoice, "effective_due_date"))} />
              {str(invoice, "sent_date") && (
                <DRow icon={<Send size={14} />} label="Sent" value={formatDate(str(invoice, "sent_date"))} />
              )}
              <DRow icon={<FolderKanban size={14} />} label="Project" value={deepStr(invoice, "project.title") || "—"} />
              <DRow icon={<FileText size={14} />} label="Contract" value={deepStr(invoice, "contract.title") || "—"} />
              <DRow icon={<Banknote size={14} />} label="Currency" value={str(invoice, "currency") || "EUR"} />
              <DRow icon={<Receipt size={14} />} label="Tax" value={taxTreatment(invoiceTaxCategory, invoiceVatRate)} />
              {/* Only shown when the invoice currency differs from the primary one. */}
              {str(invoice, "fx_rate_formatted") && (
                <DRow icon={<Banknote size={14} />} label="Exchange rate" value={str(invoice, "fx_rate_formatted")} />
              )}
              {str(invoice, "total_primary_formatted") && (
                <DRow icon={<Banknote size={14} />} label="Converted total" value={str(invoice, "total_primary_formatted")} />
              )}
              {isRem && num(invoice, "reminder_fee") > 0 && (
                <DRow icon={<Banknote size={14} />} label="Reminder Fee" value={String(num(invoice, "reminder_fee"))} />
              )}
              {/* A deposit bills one milestone of the contract's schedule —
                  say which, and how large a share of the contract it is. */}
              {isDeposit(invoice) && (() => {
                const contract = subEntity(invoice, "contract");
                const milestoneId = num(invoice, "milestone_id");
                const milestone = contract
                  ? entityList(contract, "payment_milestones").find((m) => m.id === milestoneId)
                  : undefined;
                const pct = milestone ? num(milestone, "percentage") : 0;
                return (
                  <>
                    <DRow icon={<Milestone size={14} />} label="Milestone"
                      value={depositLabel ? `${depositLabel}${pct ? ` — ${pct}%` : ""}` : "—"} />
                    <DRow icon={<FileText size={14} />} label="Contract total"
                      value={contract ? str(contract, "fixed_price_formatted") || "—" : "—"} />
                  </>
                );
              })()}
            </div>
          </Section>

          {(() => {
            const contract = subEntity(invoice, "contract");
            const milestones = contract ? entityList(contract, "payment_milestones") : [];
            if (milestones.length === 0) return null;

            const contractId = num(invoice, "contract_id");
            const projectId = num(invoice, "project_id");
            const deposits = allInvoices.filter(
              (i) => isDeposit(i) && num(i, "contract_id") === contractId && num(i, "project_id") === projectId,
            );
            const depositByMilestone = new Map<number, Entity>();
            for (const d of deposits) {
              const mid = num(d, "milestone_id");
              if (mid) depositByMilestone.set(mid, d);
            }
            const finalInv = allInvoices.find(
              (i) => isFinalInvoice(i) && num(i, "contract_id") === contractId && num(i, "project_id") === projectId,
            );

            return (
              <Section title="Payment Schedule">
                <div className="space-y-1">
                  {milestones.map((m) => {
                    // A milestone with no deposit of its own is covered by the
                    // final invoice, which settles everything the deposits left.
                    const dep = depositByMilestone.get(m.id);
                    const billedBy = dep ?? finalInv;
                    return (
                      <div key={m.id} className="flex items-center justify-between px-3 py-2 rounded-md text-xs border bg-bg-card border-border-subtle">
                        <div className="flex items-center gap-2 min-w-0">
                          <Milestone size={12} className="shrink-0 text-tertiary" />
                          <span className="font-medium truncate">{str(m, "title") || "Untitled"}</span>
                          {billedBy && (
                            <span className="text-tertiary shrink-0">{str(billedBy, "number")}</span>
                          )}
                          {!dep && finalInv && (
                            <span className="text-[10px] font-medium text-blue-300 shrink-0">via final invoice</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-secondary tabular-nums">{num(m, "percentage")}%</span>
                          {billedBy
                            ? <StatusBadge status={invoiceStatus(billedBy)} />
                            : <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-bg-hover text-tertiary">Open</span>}
                        </div>
                      </div>
                    );
                  })}
                  {finalInv && (
                    <div className="flex items-center justify-between px-3 py-2 rounded-md text-xs bg-blue-500/5 border border-blue-500/20">
                      <div className="flex items-center gap-2">
                        <FileText size={12} className="text-blue-400" />
                        <span className="font-medium text-blue-300">Final invoice</span>
                        <span className="text-tertiary">{str(finalInv, "number")}</span>
                      </div>
                      <StatusBadge status={invoiceStatus(finalInv)} />
                    </div>
                  )}
                </div>
              </Section>
            );
          })()}

          {chain.length > 1 && (
            <Section title="Reminder Chain">
              <div className="space-y-1">
                {chain.map((item) => {
                  const isThis = item.id === invoice.id;
                  const rem = isReminder(item);
                  return (
                    <div key={item.id} className={`flex items-center justify-between px-3 py-2 rounded-md text-xs
                      ${isThis ? "bg-accent/10 border border-accent/30" : "bg-bg-card border border-border-subtle"}`}>
                      <div className="flex items-center gap-2">
                        {rem
                          ? <AlertTriangle size={12} className="text-amber-500" />
                          : <FileText size={12} className="text-tertiary" />}
                        <span className="font-medium">{rem ? `Reminder ${num(item, "reminder_level")}` : str(item, "number")}</span>
                        <span className="text-tertiary">{formatDate(str(item, "date"))}</span>
                      </div>
                      <StatusBadge status={invoiceStatus(item)} />
                    </div>
                  );
                })}
              </div>
            </Section>
          )}

          {/* Deposit chain — final invoice shows its deposits */}
          {isFinalInvoice(invoice) && (() => {
            const deposits = allInvoices.filter((i) => isDeposit(i) && depositChainHeadId(i) === invoice.id);
            if (deposits.length === 0) return null;
            return (
              <Section title="Deposit Chain">
                <div className="space-y-1">
                  {deposits.map((dep) => (
                    <div key={dep.id} className="flex items-center justify-between px-3 py-2 rounded-md text-xs bg-bg-card border border-border-subtle">
                      <div className="flex items-center gap-2 min-w-0">
                        <Milestone size={12} className="text-blue-400 shrink-0" />
                        <span className="font-medium text-blue-400 truncate">
                          {depositMilestoneLabel(dep) || "Deposit"}
                        </span>
                        <span className="text-tertiary shrink-0">{str(dep, "number")}</span>
                        <span className="text-tertiary shrink-0">{formatDate(str(dep, "date"))}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-secondary tabular-nums">{str(dep, "total_formatted")}</span>
                        <StatusBadge status={invoiceStatus(dep)} />
                      </div>
                    </div>
                  ))}
                  <div className="flex items-center justify-between px-3 py-2 rounded-md text-xs bg-accent/10 border border-accent/30 font-medium">
                    <span>Remaining balance</span>
                    <span className="tabular-nums">{str(invoice, "remaining_balance_formatted")}</span>
                  </div>
                </div>
              </Section>
            );
          })()}

          {/* Deposit invoice — show which final it belongs to */}
          {isDeposit(invoice) && (() => {
            const finalId = depositChainHeadId(invoice);
            const final_ = finalId ? allInvoices.find((i) => i.id === finalId) : null;
            return final_ ? (
              <Section title="Final Invoice">
                <div className="flex items-center justify-between px-3 py-2 rounded-md text-xs bg-bg-card border border-border-subtle">
                  <div className="flex items-center gap-2">
                    <FileText size={12} className="text-blue-400" />
                    <span className="font-medium">{str(final_, "number")}</span>
                    <span className="text-tertiary">{formatDate(str(final_, "date"))}</span>
                  </div>
                  <StatusBadge status={invoiceStatus(final_)} />
                </div>
              </Section>
            ) : null;
          })()}

        </div>
      )}

      {reminderDialogOpen && (
        <CreateReminderDialog
          invoiceId={invoice.id}
          invoiceNumber={str(invoice, "number")}
          onClose={() => setReminderDialogOpen(false)}
          onCreated={(newId, warning) => { setReminderDialogOpen(false); onReminderCreated(newId, warning); }}
        />
      )}
    </div>
  );
}

function TabBtn({ label, icon, active, disabled, onClick }: {
  label: string; icon: React.ReactNode; active: boolean; disabled?: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium transition-colors border-b-2 -mb-px
        ${active ? "border-accent text-primary" : "border-transparent text-tertiary hover:text-secondary"}
        ${disabled ? "opacity-40 cursor-default" : ""}`}>
      {icon}{label}
    </button>
  );
}

function AmountCard({ label, value, color, prominent }: { label: string; value: string; color?: string; prominent?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-2 px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle"
      style={prominent ? { borderColor: `${color || "#007AFF"}44` } : undefined}>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-tertiary">{label}</span>
      <span className={`tabular-nums ${prominent ? "text-sm font-bold" : "text-xs font-medium"}`}
        style={prominent ? { color: color || "#007AFF" } : undefined}>{value || "—"}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <div><div className="text-xs font-semibold uppercase tracking-wider text-secondary mb-2">{title}</div>{children}</div>;
}

function DRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-tertiary">{icon}</span>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-tertiary">{label}</div>
        <div className="text-sm">{value}</div>
      </div>
    </div>
  );
}

function ActionBtn({ label, icon, color, active, onClick }: {
  label: string; icon: React.ReactNode; color: string; active: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
      style={{ background: active ? color : `${color}18`, color: active ? "#fff" : color }}>
      {icon}{label}
    </button>
  );
}

function CreateReminderDialog({ invoiceId, invoiceNumber, onClose, onCreated }: {
  invoiceId: number; invoiceNumber: string; onClose: () => void; onCreated: (newId?: number, warning?: string | null) => void;
}) {
  const today = new Date().toISOString().slice(0, 10);
  const twoWeeks = new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10);
  const [reminderDate, setReminderDate] = useState(today);
  const [newDueDate, setNewDueDate] = useState(twoWeeks);
  const [fee, setFee] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!newDueDate) { setError("New due date is required"); return; }
    setSubmitting(true);
    setError("");
    const params: Record<string, unknown> = {
      invoice_id: invoiceId,
      reminder_date: reminderDate,
      new_due_date: newDueDate,
    };
    const feeNum = parseFloat(fee);
    if (feeNum > 0) params.reminder_fee = feeNum;
    const res = await rpc<{ id?: number }>("invoicing.create_reminder", params);
    if (res.ok) {
      onCreated(res.data?.id, res.warning);
    } else {
      setError(res.error || "Failed to create reminder");
    }
    setSubmitting(false);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-bg-content rounded-xl border border-border-subtle shadow-2xl w-[420px]"
        onClick={(e) => e.stopPropagation()}>
        <div className="px-5 py-4 border-b border-border-subtle">
          <h2 className="text-base font-semibold">Create Reminder</h2>
          <p className="text-xs text-tertiary mt-0.5">for invoice {invoiceNumber}</p>
        </div>
        <div className="px-5 py-4 space-y-4">
          <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>
          <label className="block">
            <span className="text-[10px] font-semibold text-muted uppercase">Reminder Date<span className="text-accent ml-0.5">*</span></span>
            <input type="date" value={reminderDate} onChange={(e) => setReminderDate(e.target.value)}
              className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary" />
          </label>
          <label className="block">
            <span className="text-[10px] font-semibold text-muted uppercase">New Due Date<span className="text-accent ml-0.5">*</span></span>
            <input type="date" value={newDueDate} onChange={(e) => setNewDueDate(e.target.value)}
              className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary" />
          </label>
          <label className="block">
            <span className="text-[10px] font-semibold text-muted uppercase">Reminder Fee (optional)</span>
            <input type="number" min="0" step="0.01" placeholder="0.00" value={fee}
              onChange={(e) => setFee(e.target.value)}
              className="mt-1 w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary tabular-nums" />
          </label>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>
        <div className="px-5 py-3 border-t border-border-subtle flex justify-end gap-2">
          <button onClick={onClose}
            className="px-4 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
            Cancel
          </button>
          <button onClick={submit} disabled={submitting}
            className="px-4 py-1.5 rounded-md text-sm font-medium bg-amber-500 text-white hover:bg-amber-500/90 transition-colors disabled:opacity-50">
            {submitting ? "Creating…" : "Create Reminder"}
          </button>
        </div>
      </div>
    </div>
  );
}

function depositGroupKey(inv: Entity): string {
  return `${num(inv, "contract_id")}-${num(inv, "project_id")}`;
}

function buildChains(invoices: Entity[]): InvoiceChain[] {
  const roots: Entity[] = [];
  const reminders: Entity[] = [];
  const linkedDeposits: Entity[] = [];
  const orphanDeposits: Entity[] = [];
  const finalsByGroup = new Map<string, Entity>();

  for (const inv of invoices) {
    if (isReminder(inv)) {
      reminders.push(inv);
    } else if (isFinalInvoice(inv)) {
      roots.push(inv);
      finalsByGroup.set(depositGroupKey(inv), inv);
    } else if (isDeposit(inv)) {
      if (depositChainHeadId(inv) != null) linkedDeposits.push(inv);
      else orphanDeposits.push(inv);
    } else {
      roots.push(inv);
    }
  }

  const reminderMap = new Map<number, Entity[]>();
  const depositMap = new Map<number, Entity[]>();
  for (const root of roots) {
    reminderMap.set(root.id, []);
    depositMap.set(root.id, []);
  }

  for (const rem of reminders) {
    const headId = rem.reminder_chain_head_id as number | undefined;
    if (headId != null && reminderMap.has(headId)) {
      reminderMap.get(headId)!.push(rem);
    }
  }

  for (const dep of linkedDeposits) {
    const headId = depositChainHeadId(dep);
    if (headId != null && depositMap.has(headId)) {
      depositMap.get(headId)!.push(dep);
    } else {
      orphanDeposits.push(dep);
    }
  }

  const orphanByGroup = new Map<string, Entity[]>();
  for (const dep of orphanDeposits) {
    const key = depositGroupKey(dep);
    if (!orphanByGroup.has(key)) orphanByGroup.set(key, []);
    orphanByGroup.get(key)!.push(dep);
  }

  for (const [key, deps] of orphanByGroup) {
    const sorted = [...deps].sort(
      (a, b) => str(a, "date").localeCompare(str(b, "date")) || a.id - b.id,
    );
    const finalInv = finalsByGroup.get(key);
    if (finalInv && depositMap.has(finalInv.id)) {
      depositMap.get(finalInv.id)!.push(...sorted);
      continue;
    }
    const [head, ...rest] = sorted;
    roots.push(head);
    reminderMap.set(head.id, []);
    depositMap.set(head.id, rest);
  }

  return roots.map((root) => {
    const rems = (reminderMap.get(root.id) || []).sort(
      (a, b) => num(a, "reminder_level") - num(b, "reminder_level"),
    );
    const deps = (depositMap.get(root.id) || []).sort(
      (a, b) => str(a, "date").localeCompare(str(b, "date")) || a.id - b.id,
    );
    return { root, reminders: rems, deposits: deps };
  });
}
