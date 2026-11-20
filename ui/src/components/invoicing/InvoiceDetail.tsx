import { useEffect, useRef, useState, useMemo } from "react";
import {
  FileText, Send, CheckCircle, XCircle, Mail, Trash2, FolderKanban, Calendar, Banknote, Eye, Clock, AlertTriangle, ChevronDown, ChevronRight, Share, Receipt, Milestone, RotateCcw,
} from "lucide-react";
import { rpc, readFileAsDataURL } from "../../api/rpc";
import { str, num, bool, entity as subEntity, list as entityList, formatDate, formatMoney, localDateIso, invoiceStatus, deepStr, isReminder, isDeposit, isFinalInvoice, reminderLevel, depositChainHeadId, depositMilestoneLabel } from "../../api/entity";
import { taxCategory, taxTreatment } from "../../api/tax";
import { StatusBadge } from "../shared/StatusBadge";
import { Section } from "../shared/Section";
import type { Entity } from "../../api/types";
import { CreateReminderDialog } from "./CreateReminderDialog";
import { MiniCalendar } from "../shared/MiniCalendar";

export function InvoiceDetail({ invoice, allInvoices, onToggleSent, onTogglePaid, onToggleCancelled, onSendMail, onDelete, deleteError, mailError, onClearMailError, onReminderCreated, onRefresh }: {
  invoice: Entity; allInvoices: Entity[];
  onToggleSent: () => void; onTogglePaid: (paidDate?: string) => void; onToggleCancelled: () => void; onSendMail: () => void;
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
  // The final invoice whose settlement this document states: itself, or the one a reminder chases.
  const settlement = isFinalInvoice(invoice) ? invoice
    : isRem && chain[0] && isFinalInvoice(chain[0]) ? chain[0] : null;
  const reminderFee = isRem ? num(invoice, "reminder_fee") : 0;

  const [detailTab, setDetailTab] = useState<"invoice" | "timesheet" | "details">(pdfPath ? "invoice" : "details");
  const [pdfDataUrl, setPdfDataUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [tsPdfDataUrl, setTsPdfDataUrl] = useState<string | null>(null);
  const [tsPdfLoading, setTsPdfLoading] = useState(false);
  const [tsRendering, setTsRendering] = useState(false);
  const [tsError, setTsError] = useState("");
  const [reminderDialogOpen, setReminderDialogOpen] = useState(false);
  const [paidDateError, setPaidDateError] = useState("");

  async function changePaidDate(paidDate: string) {
    if (!paidDate) return;
    setPaidDateError("");
    const res = await rpc("invoicing.set_paid_date", { id: invoice.id, paid_date: paidDate });
    if (!res.ok) setPaidDateError(res.error || "The payment date could not be changed.");
    onRefresh();
  }
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
          <div className="w-10 h-10 rounded-lg bg-bg-card flex items-center justify-center shrink-0">
            {isRem
              ? <AlertTriangle size={18} className="text-status-warning" />
              : isFinalInvoice(invoice)
              ? <FileText size={18} className="text-status-info" />
              : isDeposit(invoice)
              ? <Milestone size={18} className="text-status-info" />
              : <FileText size={18} className="text-secondary" />}
          </div>
          <div className="min-w-0">
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
                <span className="text-xs font-medium text-status-info">Settlement invoice</span>
              )}
              <span className="text-sm text-secondary">{deepStr(invoice, "contract.client.name") || "No client"}</span>
              <StatusMenu key={invoice.id} status={status} isSent={isSent} isPaid={isPaid} isCancelled={isCancelled}
                onToggleSent={onToggleSent} onTogglePaid={onTogglePaid} onToggleCancelled={onToggleCancelled} />
            </div>
          </div>
        </div>

        {/* A final invoice settles the whole contract, and a reminder for it
            restates that settlement: what matters is the balance still due
            after deducting the deposits, not the full total. */}
        <div className="flex flex-wrap gap-2">
          {settlement ? (
            <>
              <AmountCard label="Contract total" value={str(settlement, "total_formatted")} />
              <AmountCard label="Deposits deducted" value={str(settlement, "deposits_deducted_formatted") ? `−${str(settlement, "deposits_deducted_formatted")}` : "—"} />
              {reminderFee > 0 && (
                <AmountCard label="Reminder fee" value={formatMoney(reminderFee, str(invoice, "currency") || "EUR")} />
              )}
              <AmountCard label="Balance due" value={str(invoice, "remaining_balance_formatted")} prominent />
            </>
          ) : (
            <>
              <AmountCard label="Subtotal" value={str(invoice, "sum_formatted")} />
              <AmountCard label="VAT" value={invoiceTaxCategory === "O" ? "—" : str(invoice, "vat_total_formatted")} />
              <AmountCard label="Total" value={str(invoice, "total_formatted")} prominent />
            </>
          )}
        </div>

        {/* Document actions; status changes live in the status menu above. */}
        <div>
          {mailError && (
            <div className="mb-2 flex items-center gap-2 px-3 py-2 rounded-md text-xs text-status-danger bg-status-danger/10 border border-status-danger/30">
              <span className="flex-1">{mailError}</span>
              <button onClick={onClearMailError} className="text-status-danger hover:text-status-danger">✕</button>
            </div>
          )}
          <div className="flex flex-wrap items-center gap-1.5">
            {!isCancelled && !isSent && !isPaid && pdfPath && (
              <button onClick={onSendMail}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-accent text-on-fill hover:bg-accent/90 transition-colors">
                <Mail size={13} /> {isRem ? "Send Reminder" : "Send Invoice"}
              </button>
            )}
            {canCreateReminder && (
              <button onClick={() => setReminderDialogOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-status-warning text-on-fill hover:bg-status-warning/90 transition-colors">
                <AlertTriangle size={13} /> Create Reminder
              </button>
            )}
            {!isCancelled && pdfPath && (
              <ExportLink href={pdfDataUrl ?? ""} path={pdfPath} fallbackName="invoice.pdf" label="Export Invoice" />
            )}
            {!isCancelled && tsPdfDataUrl && (
              <ExportLink href={tsPdfDataUrl} path={tsPath} fallbackName="timesheet.pdf" label="Export Timesheet" />
            )}
            <div className="flex-1" />
            {!deleteConfirm ? (
              <button onClick={() => setDeleteConfirm(true)}
                className="p-1.5 rounded-md text-secondary hover:text-status-danger border border-border-subtle transition-colors"
                title="Delete invoice">
                <Trash2 size={14} />
              </button>
            ) : (
              <div className="flex items-center gap-1.5 ml-1">
                <span className="text-xs text-status-danger">Delete permanently?</span>
                <button onClick={() => { setDeleteConfirm(false); onDelete(); }}
                  className="px-2 py-1 rounded-md text-xs font-medium bg-status-danger text-on-fill hover:bg-status-danger/90 transition-colors">
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
            <div className="mt-1.5 px-3 py-2 rounded-md text-xs text-status-danger bg-status-danger/10 border border-status-danger/30">{deleteError}</div>
          )}
        </div>

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
              <PdfPreview src={pdfDataUrl} />
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
              <PdfPreview src={tsPdfDataUrl} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-tertiary">
              <FileText size={36} strokeWidth={1.2} />
              <div className="text-sm text-center">No timesheet PDF generated yet.</div>
              <button onClick={renderTimesheet}
                className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-accent text-on-fill hover:bg-accent/90 transition-colors">
                <FileText size={14} /> Generate Timesheet PDF
              </button>
              {tsError && <p className="text-xs text-status-danger">{tsError}</p>}
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
                      <span>{str(item, "quantity_formatted")} {str(item, "unit") || "hour"}</span>
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
              {isPaid && (
                <div className="flex items-center gap-2">
                  <span className="text-tertiary"><CheckCircle size={14} /></span>
                  <label>
                    <div className="text-xs font-semibold uppercase tracking-wider text-tertiary">Paid</div>
                    <input type="date" key={str(invoice, "revenue_date")} defaultValue={str(invoice, "revenue_date")}
                      onChange={(e) => changePaidDate(e.target.value)} title="Revenue counts on the payment date"
                      className="text-sm bg-transparent text-primary rounded hover:bg-bg-hover" />
                    {paidDateError && <div className="text-xs text-status-danger">{paidDateError}</div>}
                  </label>
                </div>
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
                            <span className="text-[10px] font-medium text-status-info shrink-0">via final invoice</span>
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
                    <div className="flex items-center justify-between px-3 py-2 rounded-md text-xs bg-status-info/5 border border-status-info/20">
                      <div className="flex items-center gap-2">
                        <FileText size={12} className="text-status-info" />
                        <span className="font-medium text-status-info">Final invoice</span>
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
                          ? <AlertTriangle size={12} className="text-status-warning" />
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
                        <Milestone size={12} className="text-status-info shrink-0" />
                        <span className="font-medium text-status-info truncate">
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
                    <FileText size={12} className="text-status-info" />
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

function AmountCard({ label, value, prominent }: { label: string; value: string; prominent?: boolean }) {
  return (
    <div className={`flex-1 min-w-fit flex items-baseline justify-between gap-2 px-3 py-1.5 rounded-md bg-bg-card border
      ${prominent ? "border-accent/25" : "border-border-subtle"}`}>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-tertiary">{label}</span>
      <span className={`tabular-nums ${prominent ? "text-sm font-bold text-accent" : "text-xs font-medium"}`}>{value || "—"}</span>
    </div>
  );
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

/** Chromium's PDF viewer without its thumbnail pane or dark toolbar (the
 *  Export buttons cover download), fitted to width. The embed overscans by
 *  4px so the viewer's dark page margin is clipped away. */
function PdfPreview({ src }: { src: string }) {
  return (
    <div className="h-full rounded-lg border border-border-subtle overflow-hidden">
      <embed src={`${src}#toolbar=0&navpanes=0&view=FitH`} type="application/pdf"
        className="block -m-1 w-[calc(100%+8px)] h-[calc(100%+8px)]" />
    </div>
  );
}

function ExportLink({ href, path, fallbackName, label }: { href: string; path: string; fallbackName: string; label: string }) {
  return (
    <a href={href} download={(path.split(/[\\/]/).pop() ?? fallbackName).replace(/[<>:"/\\|?*]+/g, "_")}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-bg-sidebar text-secondary border border-border-subtle hover:bg-bg-card hover:text-primary transition-colors">
      <Share size={13} /> {label}
    </a>
  );
}

type StatusTransition = { label: string; icon: React.ReactNode; onClick: () => void; picksDate?: boolean };

/** The invoice status as a badge that opens the transitions valid from it.
 *  "Mark as paid" unfolds a calendar: revenue counts on the day the payment came in. */
function StatusMenu({ status, isSent, isPaid, isCancelled, onToggleSent, onTogglePaid, onToggleCancelled }: {
  status: string; isSent: boolean; isPaid: boolean; isCancelled: boolean;
  onToggleSent: () => void; onTogglePaid: (paidDate?: string) => void; onToggleCancelled: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [pickingDate, setPickingDate] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) { if (e.key === "Escape") setOpen(false); }
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const transitions: StatusTransition[] = [];
  if (isCancelled) {
    transitions.push({ label: "Restore", icon: <RotateCcw size={14} className="text-tertiary" />, onClick: onToggleCancelled });
  } else {
    if (!isSent && !isPaid) transitions.push({ label: "Mark as sent", icon: <Send size={14} className="text-status-info" />, onClick: onToggleSent });
    if (isSent && !isPaid) {
      transitions.push({ label: "Mark as paid", icon: <CheckCircle size={14} className="text-status-success" />, onClick: () => setPickingDate((p) => !p), picksDate: true });
      transitions.push({ label: "Back to draft", icon: <RotateCcw size={14} className="text-tertiary" />, onClick: onToggleSent });
    }
    if (isPaid) transitions.push({ label: "Mark as unpaid", icon: <RotateCcw size={14} className="text-tertiary" />, onClick: () => onTogglePaid() });
    transitions.push({ label: "Cancel invoice", icon: <XCircle size={14} className="text-status-warning" />, onClick: onToggleCancelled });
  }
  const item = "flex items-center gap-2 w-full px-3 py-1.5 text-sm text-left text-secondary hover:bg-bg-hover hover:text-primary transition-colors";

  return (
    <div ref={ref} className="relative" data-status-menu>
      <button onClick={() => { setOpen((o) => !o); setPickingDate(false); }} title="Change status" aria-haspopup="menu" aria-expanded={open}
        className={`flex items-center gap-0.5 rounded-full pr-1 transition-colors ${open ? "bg-bg-hover" : "hover:bg-bg-hover"}`}>
        <StatusBadge status={status} />
        <ChevronDown size={12} className="text-tertiary" />
      </button>
      {open && (
        <div role="menu" className="absolute top-full left-0 mt-1 z-50 min-w-[160px] py-1 rounded-lg bg-bg-sidebar border border-border-subtle shadow-lg">
          {transitions.map((t) => t.picksDate ? (
            <div key={t.label} className={pickingDate ? "bg-surface-overlay" : ""}>
              <button role="menuitem" aria-expanded={pickingDate} onClick={t.onClick}
                className={`${item} ${pickingDate ? "text-primary" : ""}`}>
                {t.icon}<span className="flex-1">{t.label}</span>
                <ChevronRight size={12} className={`text-tertiary transition-transform ${pickingDate ? "rotate-90" : ""}`} />
              </button>
              {pickingDate && (
                <div className="unfold px-2 pb-2">
                  <MiniCalendar max={localDateIso()} dayLabel={(iso) => `Paid on ${formatDate(iso)}`}
                    onPick={(iso) => { setOpen(false); onTogglePaid(iso); }} />
                </div>
              )}
            </div>
          ) : (
            <button key={t.label} role="menuitem" onClick={() => { setOpen(false); t.onClick(); }} className={item}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
