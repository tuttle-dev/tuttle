import { Building2, FolderKanban, Calendar, AlertTriangle, Milestone } from "lucide-react";
import { str, formatDate, deepStr, isDeposit, isFinalInvoice, depositMilestoneLabel, milestoneScheduleStatus, type MilestoneScheduleStatus } from "../../api/entity";
import type { Entity } from "../../api/types";
import { DocumentTypeBadge, MilestoneScheduleBadge } from "./InvoiceRows";
import type { InvoiceChain } from "./chains";

export function InvoiceChainCard({ chain, color, reminderCount, depositCount }: {
  chain: InvoiceChain; color: string; reminderCount?: number; depositCount?: number;
}) {
  const { root, deposits } = chain;
  const schedule = milestoneScheduleStatus(root, deposits);
  return (
    <div className="space-y-1.5">
      <InvoiceCard invoice={root} color={color} reminderCount={reminderCount} depositCount={depositCount} schedule={schedule} />
      {deposits.length > 0 && (
        <div className="ml-2 pl-2 border-l-2 border-status-info/60 space-y-1.5">
          {deposits.map((dep) => (
            <div key={dep.id} className="pt-1 border-t border-border-subtle/60 first:border-t-0 first:pt-0">
              <div className="flex items-center gap-1 min-w-0">
                <span className="text-xs font-semibold text-status-info truncate">
                  {depositMilestoneLabel(dep) || "Deposit"}
                </span>
                <DocumentTypeBadge type="deposit" />
              </div>
              <div className="flex flex-wrap items-baseline gap-x-2 mt-0.5">
                <span className="text-[10px] text-tertiary truncate">{str(dep, "number") || "Draft"}</span>
                <span className="ml-auto text-xs font-semibold tabular-nums shrink-0">{str(dep, "total_formatted")}</span>
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
  const number = str(invoice, "number") || "Draft";
  const hasBadges = isDeposit(invoice) || isFinal || (depositCount ?? 0) > 0 || (reminderCount ?? 0) > 0;
  return (
    <div className="space-y-1.5">
      {/* Amount wraps below the number when the column is too narrow for both. */}
      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="text-sm font-semibold truncate" title={number}>{number}</span>
        <span className="ml-auto text-sm font-bold tabular-nums shrink-0">{str(invoice, "total_formatted")}</span>
      </div>
      {hasBadges && (
        <div className="flex flex-wrap items-center gap-1">
          {isDeposit(invoice) && depositLabel && (
            <span className="text-xs font-semibold text-status-info truncate">{depositLabel}</span>
          )}
          {isFinal && (
            <span className="text-xs font-semibold text-status-info truncate">Settlement</span>
          )}
          {isDeposit(invoice) && <DocumentTypeBadge type="deposit" />}
          {isFinal && <DocumentTypeBadge type="final" />}
          {(depositCount ?? 0) > 0 && !isDeposit(invoice) && (
            <span className="flex items-center gap-0.5 px-1 py-0.5 rounded text-[10px] font-semibold bg-status-info/15 text-status-info">
              <Milestone size={9} />{depositCount}
            </span>
          )}
          {(reminderCount ?? 0) > 0 && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-status-warning/15 text-status-warning">
              <AlertTriangle size={9} />{reminderCount}
            </span>
          )}
        </div>
      )}
      {deepStr(invoice, "contract.client.name") && (
        <div className="flex items-center gap-1 text-secondary">
          <Building2 size={12} className="text-tertiary shrink-0" />
          <span className="text-xs truncate">{deepStr(invoice, "contract.client.name")}</span>
        </div>
      )}
      {str(invoice, "project_titles") && (
        <div className="flex items-center gap-1 text-secondary">
          <FolderKanban size={12} className="text-tertiary shrink-0" />
          <span className="text-xs truncate">{str(invoice, "project_titles")}</span>
        </div>
      )}
      <div className="flex items-center gap-1 text-tertiary">
        <Calendar size={12} className="shrink-0" /><span className="text-xs truncate">{formatDate(str(invoice, "date"))}</span>
      </div>
      {schedule && (
        <div className="pt-0.5">
          <MilestoneScheduleBadge schedule={schedule} />
        </div>
      )}
    </div>
  );
}
