import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { FileText, Plus, AlertTriangle } from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num, bool, invoiceStatus, deepStr, milestoneScheduleStatus } from "../../api/entity";
import { statusColor } from "../shared/status-colors";
import { ViewModeToggle } from "../shared/ViewModeToggle";
import { KanbanBoard, useStageStore, type BoardColumn } from "../shared/KanbanBoard";
import { Toolbar, ToolbarButtonPrimary, ToolbarFilterGroup, ListDetailLayout } from "../shared/ToolbarButtons";
import { useNavigation } from "../shared/NavigationContext";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { useAutoSelect } from "../../hooks/useAutoSelect";
import { LoadError, LoadingState } from "../shared/LoadStates";
import type { Entity } from "../../api/types";
import { CreateInvoiceDialog } from "./CreateInvoiceDialog";
import { chainAccentClass, InvoiceRow, ReminderRow, DepositRow } from "./InvoiceRows";
import { InvoiceChainCard } from "./InvoiceCards";
import { InvoiceDetail } from "./InvoiceDetail";
import { type InvoiceChain, buildChains } from "./chains";

const INVOICE_COLUMNS: BoardColumn[] = ["Draft", "Sent", "Overdue", "Paid", "Cancelled"]
  .map((id) => ({ id, label: id, color: statusColor(id) }));

const STATUS_FILTERS = ["All", "Draft", "Sent", "Paid", "Overdue", "Cancelled"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const FILTER_COLORS: Record<string, string> = {
  ...Object.fromEntries(STATUS_FILTERS.map((s) => [s, statusColor(s)])),
  All: "var(--color-status-info)",
};

export function InvoicingView() {
  const { filter: navFilter } = useNavigation();
  const [invoices, setInvoices] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [viewMode, setViewMode] = useState<"list" | "board">("list");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(
    () => STATUS_FILTERS.find((f) => f === navFilter.invoiceStatus) ?? "All");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(!!navFilter.newInvoice);
  const [newlyCreatedId, setNewlyCreatedId] = useState<number | null>(null);
  const [mailError, setMailError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [renderWarning, setRenderWarning] = useState<string | null>(null);

  const defaultColumn = useCallback(
    (e: { id: number; [k: string]: unknown }) => invoiceStatus(e as Entity), [],
  );
  const stageStore = useStageStore("invoice", INVOICE_COLUMNS, defaultColumn);

  useEffect(() => { load(navFilter.invoiceId); }, []);
  // An invoice opened from elsewhere (e.g. an overdue task) is scrolled into view once.
  const navScrolled = useRef(false);
  useEffect(() => {
    if (navScrolled.current || navFilter.invoiceId == null || invoices.length === 0) return;
    navScrolled.current = true;
    document.querySelector(`[data-invoice-id="${navFilter.invoiceId}"]`)?.scrollIntoView({ block: "center" });
  }, [invoices]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setMailError(null); setStatusError(null); }, [selected?.id]);

  async function load(selectId?: number) {
    setLoading(true);
    setLoadFailed(false);
    const res = await rpc<Entity[]>("invoicing.get_all");
    setLoadFailed(!res.ok);
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

  useAutoSelect(invoices, chains.flatMap((c) => [c.root, ...c.deposits, ...c.reminders]), selected, setSelected, {
    preferred: navFilter.contractId != null ? (inv) => num(inv, "contract_id") === navFilter.contractId : undefined,
  });

  // A status change can be refused, e.g. cancelling a deposit that a final invoice settles.
  async function toggleStatus(method: "toggle_sent" | "toggle_paid" | "toggle_cancelled", id: number, params: Record<string, unknown> = {}) {
    setStatusError(null);
    const res = await rpc(`invoicing.${method}`, { id, ...params });
    if (!res.ok) setStatusError(res.error || "The invoice status could not be changed.");
    load();
  }
  async function toggleSent(id: number) { await toggleStatus("toggle_sent", id); }
  async function togglePaid(id: number, paidDate?: string) { await toggleStatus("toggle_paid", id, paidDate ? { paid_date: paidDate } : {}); }
  async function toggleCancelled(id: number) { await toggleStatus("toggle_cancelled", id); }
  async function sendMail(id: number) {
    setMailError(null);
    const res = await rpc<void>("invoicing.send_mail", { id });
    if (!res.ok) setMailError(res.error || "Failed to send invoice");
  }
  const [deleteError, setDeleteError] = useState<string | null>(null);
  async function handleDelete(id: number) {
    setDeleteError(null);
    const res = await rpc("invoicing.delete", { id });
    if (res.ok) load();
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

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Invoicing"
        actions={<ToolbarButtonPrimary icon={<Plus size={13} />} label="New" onClick={() => setCreateOpen(true)} />}
        center={viewMode === "list"
          ? <ToolbarFilterGroup options={STATUS_FILTERS} value={statusFilter} onChange={setStatusFilter} colors={FILTER_COLORS} />
          : undefined}
        right={<ViewModeToggle mode={viewMode} onChange={setViewMode} />}
        search={{ value: search, onChange: setSearch }}
      />

      {renderWarning && (
        <div className="mx-4 mt-2 flex items-center gap-2 px-3 py-2 rounded-md text-xs text-status-warning bg-status-warning/10 border border-status-warning/30">
          <AlertTriangle size={14} className="shrink-0" />
          <span className="flex-1">{renderWarning}</span>
          <button onClick={() => setRenderWarning(null)} className="text-status-warning hover:text-status-warning/80">✕</button>
        </div>
      )}

      {statusError && (
        <div className="mx-4 mt-2 flex items-center gap-2 px-3 py-2 rounded-md text-xs text-status-danger bg-status-danger/10 border border-status-danger/30">
          <AlertTriangle size={14} className="shrink-0" />
          <span className="flex-1">{statusError}</span>
          <button onClick={() => setStatusError(null)} className="text-status-danger hover:text-status-danger/80">✕</button>
        </div>
      )}

      {loadFailed ? (
        <LoadError what="invoices" onRetry={() => load()} />
      ) : loading && invoices.length === 0 ? (
        <LoadingState />
      ) : invoices.length === 0 ? (
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
                <div key={inv.id} data-invoice-id={inv.id} className={chainAccentClass(chain)}>
                  <InvoiceRow invoice={inv} isSelected={isSelected} isHighlighted={isHighlighted}
                    reminderCount={chain.reminders.length}
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
                onTogglePaid={(paidDate) => togglePaid(selected.id, paidDate)} onToggleCancelled={() => toggleCancelled(selected.id)}
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
          projectId={navFilter.newInvoice ? navFilter.projectId : undefined}
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
