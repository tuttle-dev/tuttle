import { useEffect, useState, useCallback, useMemo } from "react";
import {
  FileText, Send, CheckCircle, XCircle, Mail, Trash2,
  Building2, FolderKanban, Calendar, Banknote, Eye, DollarSign,
  Plus, Clock, AlertTriangle, ChevronLeft, ChevronRight, Search, Share, Receipt,
} from "lucide-react";
import { rpc, readFileAsDataURL } from "../../api/rpc";
import { str, num, bool, entity as subEntity, list as entityList, formatDate, invoiceStatus, deepStr, isReminder, reminderLevel } from "../../api/entity";
import { taxCategory, taxTreatment } from "../../api/tax";
import { StatusBadge } from "../shared/StatusBadge";
import { ViewModeToggle } from "../shared/ViewModeToggle";
import { KanbanBoard, useStageStore, type BoardColumn } from "../shared/KanbanBoard";
import { Toolbar, ToolbarButtonPrimary, ToolbarFilterGroup, ListDetailLayout, LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import { useNavigation } from "../shared/NavigationContext";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import type { Entity } from "../../api/types";

type InvoiceChain = { root: Entity; reminders: Entity[] };

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
                <div key={inv.id}>
                  <InvoiceRow invoice={inv} isSelected={isSelected} isHighlighted={isHighlighted}
                    reminderCount={chain.reminders.length}
                    onSelect={() => { setNewlyCreatedId(null); setSelected(inv); }} />
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
            renderCard={(inv, col) => <InvoiceCard invoice={inv} color={col.color} reminderCount={reminderCountMap.get(inv.id) || 0} />} />
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

function makeDefaultItem(project?: Entity | null): LineItem {
  const contract = project ? (project as Record<string, unknown>).contract as Record<string, unknown> | undefined : undefined;
  const unit = contract?.unit as string | undefined;
  const rate = contract?.rate as number | undefined;
  return {
    description: project ? str(project, "title") : "",
    quantity: "",
    unit: unit ?? "hour",
    unitPrice: rate != null ? String(rate) : "",
  };
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

  const selectedProject = projects.find((p) => p.id === projectId) ?? null;
  const isFixedPrice = selectedProject ? bool(selectedProject, "is_fixed_price") : false;

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
          setLineItems([makeDefaultItem(active[0])]);
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
    setLineItems([makeDefaultItem(proj)]);
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

          {/* Fixed-price notice */}
          {isFixedPrice && selectedProject && (() => {
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

          {/* Mode toggle (time-based only) */}
          {!isFixedPrice && (
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

          {/* Timesheet opt-out (time-tracking mode only) */}
          {!isFixedPrice && mode === "timetracking" && (
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
            {!isFixedPrice && (
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

          {/* Line items editor (time-based manual only) */}
          {!isFixedPrice && mode === "manual" && (
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
            {submitting ? "Creating…" : "Create Invoice"}
          </button>
        </div>
      </div>
    </div>
  );
}

function InvoiceRow({ invoice, isSelected, isHighlighted, reminderCount, onSelect }: {
  invoice: Entity; isSelected: boolean; isHighlighted?: boolean; reminderCount?: number; onSelect: () => void;
}) {
  const status = invoiceStatus(invoice);
  return (
    <button onClick={onSelect}
      className={`w-full text-left ${LIST_ROW_PADDING} border-b transition-colors
        ${isSelected ? "bg-bg-selected border-border-subtle" : isHighlighted ? "bg-accent/10 border-accent/30" : "border-border-subtle hover:bg-bg-hover"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium">{str(invoice, "number") || "Draft"}</span>
          <span className="text-xs text-tertiary">{formatDate(str(invoice, "date"))}</span>
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
      <div className="flex items-center gap-1.5 mt-1 text-secondary">
        <span className="text-xs truncate">{deepStr(invoice, "contract.client.name") || "No client"}</span>
        {deepStr(invoice, "project.title") && (
          <><span className="text-tertiary">·</span>
          <span className="text-xs text-tertiary truncate">{deepStr(invoice, "project.title")}</span></>
        )}
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

function InvoiceCard({ invoice, reminderCount }: { invoice: Entity; color: string; reminderCount?: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold">{str(invoice, "number") || "Draft"}</span>
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
              : <FileText size={18} className="text-secondary" />}
          </div>
          <div>
            <h1 className="text-lg font-semibold">
              {isRem ? `Reminder ${reminderLevel(invoice)}` : str(invoice, "number") || "Draft"}
            </h1>
            <div className="flex items-center gap-2">
              {isRem && <span className="text-xs text-tertiary">Inv. {str(invoice, "number")}</span>}
              <span className="text-sm text-secondary">{deepStr(invoice, "contract.client.name") || "No client"}</span>
              <StatusBadge status={status} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <AmountCard label="Subtotal" value={str(invoice, "sum_formatted")} />
          <AmountCard label="VAT" value={invoiceTaxCategory === "O" ? "—" : str(invoice, "vat_total_formatted")} color="#f97316" />
          <AmountCard label="Total" value={str(invoice, "total_formatted")} prominent />
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
              <DRow icon={<FolderKanban size={14} />} label="Project" value={deepStr(invoice, "project.title") || "—"} />
              <DRow icon={<FileText size={14} />} label="Contract" value={deepStr(invoice, "contract.title") || "—"} />
              <DRow icon={<Banknote size={14} />} label="Currency" value={str(invoice, "currency") || "EUR"} />
              <DRow icon={<Receipt size={14} />} label="Tax" value={taxTreatment(invoiceTaxCategory, invoiceVatRate)} />
              {isRem && num(invoice, "reminder_fee") > 0 && (
                <DRow icon={<Banknote size={14} />} label="Reminder Fee" value={String(num(invoice, "reminder_fee"))} />
              )}
            </div>
          </Section>

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

function buildChains(invoices: Entity[]): InvoiceChain[] {
  const byId = new Map<number, Entity>();
  for (const inv of invoices) byId.set(inv.id, inv);

  const roots: Entity[] = [];
  const reminders: Entity[] = [];
  for (const inv of invoices) {
    if (isReminder(inv)) reminders.push(inv);
    else roots.push(inv);
  }

  const chainMap = new Map<number, Entity[]>();
  for (const root of roots) chainMap.set(root.id, []);

  for (const rem of reminders) {
    const headId = rem.reminder_chain_head_id as number | undefined;
    if (headId != null && chainMap.has(headId)) {
      chainMap.get(headId)!.push(rem);
    }
  }

  return roots.map((root) => {
    const rems = (chainMap.get(root.id) || []).sort(
      (a, b) => num(a, "reminder_level") - num(b, "reminder_level"),
    );
    return { root, reminders: rems };
  });
}
