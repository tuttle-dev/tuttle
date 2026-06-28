/**
 * Helpers for working with generic Entity dicts from Python.
 */

import type { Entity } from "./types";

export function str(e: Entity, key: string): string {
  const v = e[key];
  if (v == null) return "";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return String(v);
}

export function num(e: Entity, key: string): number {
  const v = e[key];
  if (v == null) return 0;
  if (typeof v === "number") return v;
  if (typeof v === "string") return parseFloat(v) || 0;
  return 0;
}

export function int(e: Entity, key: string): number {
  return Math.round(num(e, key));
}

export function bool(e: Entity, key: string): boolean {
  const v = e[key];
  if (typeof v === "boolean") return v;
  if (typeof v === "number") return v !== 0;
  return false;
}

export function entity(e: Entity, key: string): Entity | null {
  const v = e[key];
  if (v && typeof v === "object" && "id" in v) return v as Entity;
  return null;
}

/** Traverse a dot-separated path through nested entities, e.g. "contract.client.name" */
export function deep(e: Entity, path: string): unknown {
  const parts = path.split(".");
  let cur: unknown = e;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return null;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur;
}

export function deepStr(e: Entity, path: string): string {
  const v = deep(e, path);
  if (v == null) return "";
  return String(v);
}

export function list(e: Entity, key: string): Entity[] {
  const v = e[key];
  if (Array.isArray(v)) return v as Entity[];
  return [];
}

export function fullName(e: Entity): string {
  return [str(e, "first_name"), str(e, "last_name")].filter(Boolean).join(" ");
}

export function displayName(e: Entity): string {
  const name = fullName(e);
  if (name) return name;
  const company = str(e, "company");
  if (company) return company;
  const n = str(e, "name");
  if (n) return n;
  return "—";
}

export function initials(e: Entity): string {
  const parts = [str(e, "first_name"), str(e, "last_name")].filter(Boolean);
  if (parts.length === 0) {
    const name = str(e, "name");
    if (name) {
      return name
        .split(" ")
        .slice(0, 2)
        .map((w) => w[0]?.toUpperCase())
        .join("");
    }
    return "?";
  }
  return parts.map((p) => p[0]?.toUpperCase()).join("");
}

export function formatDate(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function dateRange(e: Entity): string {
  const start = str(e, "start_date");
  const end = str(e, "end_date");
  if (end) return `${formatDate(start)} – ${formatDate(end)}`;
  if (start) return `From ${formatDate(start)}`;
  return "";
}

export function projectStatus(e: Entity): string {
  const stage = str(e, "stage");
  if (stage) return stage;
  const completed = bool(e, "is_completed");
  if (completed) return "Completed";
  const end = str(e, "end_date");
  const start = str(e, "start_date");
  const today = new Date().toISOString().slice(0, 10);
  if (start > today) return "Upcoming";
  if (end && end >= today) return "Active";
  if (!end) return "Active";
  return "Completed";
}

export function invoiceStatus(e: Entity): string {
  if (bool(e, "cancelled")) return "Cancelled";
  if (bool(e, "paid")) return "Paid";
  if (bool(e, "sent")) {
    // Use effective_due_date (set by reminder) if available, else compute from contract
    const effectiveDue = str(e, "effective_due_date");
    if (effectiveDue) {
      if (new Date(effectiveDue) < new Date()) return "Overdue";
    } else {
      const contract = entity(e, "contract");
      if (contract) {
        const termDays = num(contract, "term_of_payment");
        const dateStr = str(e, "date");
        if (dateStr && termDays) {
          const due = new Date(dateStr);
          due.setDate(due.getDate() + termDays);
          if (due < new Date()) return "Overdue";
        }
      }
    }
    return "Sent";
  }
  return "Draft";
}

export function isReminder(e: Entity): boolean {
  return bool(e, "is_reminder") || str(e, "document_type") === "reminder";
}

export function isDeposit(e: Entity): boolean {
  return bool(e, "is_deposit") || str(e, "document_type") === "deposit";
}

export function isFinalInvoice(e: Entity): boolean {
  return bool(e, "is_final_invoice") || str(e, "document_type") === "final";
}

export function reminderLevel(e: Entity): number {
  return num(e, "reminder_level");
}

export function reminderChainHeadId(e: Entity): number | null {
  const v = e.reminder_chain_head_id;
  if (v == null) return null;
  return typeof v === "number" ? v : null;
}

export function depositChainHeadId(e: Entity): number | null {
  const v = e.deposit_chain_head_id;
  if (v == null) return null;
  return typeof v === "number" ? v : null;
}

/** Milestone title or first line-item description for a deposit invoice. */
export function depositMilestoneLabel(e: Entity): string {
  const title = deepStr(e, "milestone.title");
  if (title) return title;
  const items = list(e, "items");
  if (items.length > 0) {
    const desc = str(items[0], "description");
    if (desc) return desc;
  }
  return "";
}

export type MilestoneScheduleStatus = {
  /** Milestones in the contract's payment schedule. */
  total: number;
  /** Milestones already billed. */
  invoicedCount: number;
  /** Documents issued for this schedule: the deposits plus the final invoice. */
  issuedCount: number;
  /** How many of those documents are paid. */
  paidCount: number;
  hasFinal: boolean;
  /** Nothing left to bill or collect on this contract. */
  settled: boolean;
};

export function chainDepositInvoices(root: Entity, nestedDeposits: Entity[]): Entity[] {
  const deps = nestedDeposits.filter(isDeposit);
  if (isDeposit(root)) return [root, ...deps];
  return deps;
}

/** Progress of a contract's payment schedule across a grouped invoice chain.
 *
 * Derived from the invoices themselves rather than the milestones' `invoiced`
 * flags: the invoice list is what the view reloads, so a count taken from it
 * cannot go stale against a contract snapshot embedded in an older invoice.
 */
export function milestoneScheduleStatus(
  root: Entity,
  nestedDeposits: Entity[],
): MilestoneScheduleStatus | null {
  const contract = entity(root, "contract");
  if (!contract) return null;
  const total = list(contract, "payment_milestones").length;
  if (total === 0) return null;

  const deposits = chainDepositInvoices(root, nestedDeposits);
  const hasFinal = isFinalInvoice(root);
  const issued = hasFinal ? [...deposits, root] : deposits;
  const paidCount = issued.filter((inv) => invoiceStatus(inv) === "Paid").length;

  // A final invoice settles every milestone the deposits did not cover, so its
  // presence means the whole schedule has been billed out.
  const covered = new Set(deposits.map((d) => int(d, "milestone_id")).filter((id) => id > 0));
  const invoicedCount = hasFinal ? total : covered.size;

  const settled = hasFinal
    ? invoiceStatus(root) === "Paid"
    : invoicedCount === total && issued.length > 0 && paidCount === issued.length;

  return { total, invoicedCount, issuedCount: issued.length, paidCount, hasFinal, settled };
}
