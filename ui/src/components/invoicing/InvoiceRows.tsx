import { AlertTriangle } from "lucide-react";
import { str, formatDate, invoiceStatus, deepStr, isDeposit, isFinalInvoice, reminderLevel, depositMilestoneLabel, type MilestoneScheduleStatus } from "../../api/entity";
import { StatusBadge } from "../shared/StatusBadge";
import { LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import type { Entity } from "../../api/types";
import type { InvoiceChain } from "./chains";

export function DocumentTypeBadge({ type }: { type: "deposit" | "final" }) {
  if (type === "deposit") {
    return (
      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-status-info/15 text-status-info shrink-0">
        Deposit
      </span>
    );
  }
  return (
    <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-status-info/20 text-status-info shrink-0">
      Final
    </span>
  );
}

export function chainAccentClass(chain: InvoiceChain): string {
  if (isFinalInvoice(chain.root) || isDeposit(chain.root) || chain.deposits.length > 0) {
    return "border-l-2 border-l-status-info";
  }
  return "";
}

export function MilestoneScheduleBadge({ schedule }: { schedule: MilestoneScheduleStatus }) {
  const { total, invoicedCount, issuedCount, paidCount, hasFinal, settled } = schedule;

  if (settled) {
    return (
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-status-success/10 text-status-success shrink-0">
        All settled
      </span>
    );
  }
  if (hasFinal) {
    return (
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-status-info/10 text-status-info shrink-0">
        Settlement · {paidCount}/{issuedCount} paid
      </span>
    );
  }
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 ${
      invoicedCount === total ? "bg-status-info/10 text-status-info" : "bg-status-warning/10 text-status-warning"
    }`}>
      {invoicedCount}/{total} milestones invoiced · {paidCount}/{issuedCount} paid
    </span>
  );
}

// A chain's deposits are listed as rows right below it and its schedule badge
// marks a settlement, so neither gets a badge of its own here.
export function InvoiceRow({ invoice, isSelected, isHighlighted, reminderCount, schedule, onSelect }: {
  invoice: Entity; isSelected: boolean; isHighlighted?: boolean;
  reminderCount?: number; schedule?: MilestoneScheduleStatus | null; onSelect: () => void;
}) {
  const status = invoiceStatus(invoice);
  const depositLabel = depositMilestoneLabel(invoice);
  const isFinal = isFinalInvoice(invoice);
  return (
    <button onClick={onSelect}
      className={`w-full text-left ${LIST_ROW_PADDING} border-b transition-colors
        ${isSelected ? "bg-bg-selected border-border-subtle" : isHighlighted ? "bg-accent/10 border-accent/30" : "border-border-subtle hover:bg-bg-hover"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0 overflow-hidden">
          <span className="text-sm font-medium shrink-0">{str(invoice, "number") || "Draft"}</span>
          {isDeposit(invoice) && depositLabel && (
            <span className="text-xs font-semibold text-status-info truncate">{depositLabel}</span>
          )}
          <span className="text-xs text-tertiary shrink-0">{formatDate(str(invoice, "date"))}</span>
          {isDeposit(invoice) && <DocumentTypeBadge type="deposit" />}
          {isFinal && !schedule && <DocumentTypeBadge type="final" />}
          {(reminderCount ?? 0) > 0 && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-status-warning/15 text-status-warning">
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
        {str(invoice, "project_titles") && (
          <><span className="text-tertiary">·</span>
          <span className="text-xs text-tertiary truncate">{str(invoice, "project_titles")}</span></>
        )}
        {schedule && <MilestoneScheduleBadge schedule={schedule} />}
      </div>
    </button>
  );
}

export function ReminderRow({ invoice, isSelected, onSelect }: { invoice: Entity; isSelected: boolean; onSelect: () => void }) {
  const status = invoiceStatus(invoice);
  const level = reminderLevel(invoice);
  return (
    <button onClick={onSelect}
      className={`w-full text-left pl-10 pr-4 py-2.5 border-b transition-colors border-l-2 border-l-status-warning
        ${isSelected ? "bg-bg-selected border-b-border-subtle" : "border-b-border-subtle hover:bg-bg-hover bg-bg-content/50"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-semibold text-status-warning">Reminder {level}</span>
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

export function DepositRow({ invoice, isSelected, onSelect }: { invoice: Entity; isSelected: boolean; onSelect: () => void }) {
  const status = invoiceStatus(invoice);
  const depositLabel = depositMilestoneLabel(invoice);
  return (
    <button onClick={onSelect}
      className={`w-full text-left pl-10 pr-4 py-2.5 border-b transition-colors border-l-2 border-l-status-info
        ${isSelected ? "bg-bg-selected border-b-border-subtle" : "border-b-border-subtle hover:bg-bg-hover bg-bg-content/50"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0 overflow-hidden">
          <span className="text-xs font-semibold text-status-info truncate">
            {depositLabel || "Deposit"}
          </span>
          <DocumentTypeBadge type="deposit" />
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
