/**
 * Task rules as the UI sees them (see tuttle/app/tasks/rules.py): the
 * rule's fields, what the composer offers, and the sentence a rule reads as.
 */

export type RuleKind = "date" | "event";
export type OffsetUnit = "day" | "week" | "month";

export interface TaskRule {
  id?: number;
  title: string;
  note: string | null;
  kind: RuleKind;
  // On a date
  start_date: string | null;
  every: number;
  unit: "week" | "month" | null;
  // When something happens
  event: string | null;
  offset: number;
  offset_unit: OffsetUnit;
  before: boolean;
  client_id: number | null;
  paused: boolean;
  next_date?: string | null;
}

export interface RuleEvent {
  key: string;
  label: string;
  state: boolean;
  final: boolean;
  after_only: boolean;
  title_before: string | null;
  title_after: string;
}

export interface RuleRecord {
  key: string;
  label: string;
  placeholders: string[];
  events: RuleEvent[];
}

export interface RuleOptions {
  records: RuleRecord[];
  clients: { id: number; name: string }[];
}

export interface RulePreview {
  error: string | null;
  now?: { title: string; date: string }[];
  next?: { title: string; date: string } | null;
  later?: string[];
  /** A new rule on a final status (paid, completed): it counts only records that reach it from today. */
  from_today?: boolean;
}

/** How often a rule on a date repeats, as the composer offers it. */
export const REPEATS: { key: string; label: string; unit: "week" | "month" | null; every: number }[] = [
  { key: "once", label: "Once", unit: null, every: 1 },
  { key: "week", label: "Every week", unit: "week", every: 1 },
  { key: "2weeks", label: "Every 2 weeks", unit: "week", every: 2 },
  { key: "month", label: "Every month", unit: "month", every: 1 },
  { key: "quarter", label: "Every quarter", unit: "month", every: 3 },
  { key: "halfyear", label: "Every 6 months", unit: "month", every: 6 },
  { key: "year", label: "Every year", unit: "month", every: 12 },
];

export function repeatOf(rule: Pick<TaskRule, "unit" | "every">) {
  return REPEATS.find((r) => r.unit === rule.unit && (r.unit === null || r.every === rule.every));
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** A calendar date ("2026-11-06") as a local date, not UTC midnight. */
export function parseDay(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function isoDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** "Nov 6, 2026"; without the year when it is this year's. */
export function fmtDay(iso: string, withYear = false): string {
  const d = parseDay(iso);
  const short = `${MONTHS[d.getMonth()].slice(0, 3)} ${d.getDate()}`;
  return withYear || d.getFullYear() !== new Date().getFullYear() ? `${short}, ${d.getFullYear()}` : short;
}

/** "today", "in 3 days", "12 days ago". */
export function relDay(iso: string): string {
  const today = new Date();
  const n = Math.round((parseDay(iso).getTime() - new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()) / 86400000);
  if (n === 0) return "today";
  if (n === 1) return "tomorrow";
  if (n === -1) return "yesterday";
  return n > 0 ? `in ${n} days` : `${-n} days ago`;
}

function ordinal(n: number): string {
  const tens = n % 100;
  if (tens >= 11 && tens <= 13) return `${n}th`;
  return n + (["th", "st", "nd", "rd"][n % 10] ?? "th");
}

export function findEvent(options: RuleOptions | null, key: string | null): { record: RuleRecord; event: RuleEvent } | null {
  if (!options || !key) return null;
  for (const record of options.records) {
    const event = record.events.find((e) => e.key === key);
    if (event) return { record, event };
  }
  return null;
}

export function unitLabel(unit: string, n: number): string {
  return n === 1 ? unit : `${unit}s`;
}

/** The rule as a sentence: "30 days before a contract ends", "Every month on the 1st". */
export function ruleSentence(rule: TaskRule, options: RuleOptions | null): string {
  if (rule.kind === "date") {
    if (!rule.start_date) return "On a date";
    const d = parseDay(rule.start_date);
    const start = fmtDay(rule.start_date, true);
    if (!rule.unit) return `On ${start}`;
    if (rule.unit === "week") {
      return `${rule.every === 1 ? "Every week" : `Every ${rule.every} weeks`} on ${WEEKDAYS[d.getDay()]}`;
    }
    if (rule.every === 1) return `Every month on the ${ordinal(d.getDate())}`;
    if (rule.every === 12) return `Every year on ${MONTHS[d.getMonth()]} ${d.getDate()}`;
    const repeat = repeatOf(rule);
    return `${repeat ? repeat.label : `Every ${rule.every} months`}, starting ${start}`;
  }
  const found = findEvent(options, rule.event);
  if (!found) return "When something happens";
  const { record, event } = found;
  const when = rule.offset === 0
    ? (event.state ? "As soon as" : "On the day")
    : `${rule.offset} ${unitLabel(rule.offset_unit, rule.offset)} ${rule.before ? "before" : "after"}`;
  const client = rule.client_id != null ? options?.clients.find((c) => c.id === rule.client_id)?.name : null;
  return `${when} ${record.label} ${event.label}${client ? ` for ${client}` : ""}`;
}

/** Where a task about a record gets done. */
export function subjectDestination(type: string | null, id: number | null): { view: string; filter?: Record<string, number> } | undefined {
  if (!type) return undefined;
  if (type === "contract" && id != null) return { view: "contracts", filter: { contractId: id } };
  if (type === "project" && id != null) return { view: "projects", filter: { projectId: id } };
  if (type === "invoice" && id != null) return { view: "invoicing", filter: { invoiceId: id } };
  if (type === "goal") return { view: "dashboard" };
  return undefined;
}

/** A blank rule of either kind, as the composer starts it. */
export function newRule(kind: RuleKind, options: RuleOptions | null): TaskRule {
  const today = new Date();
  const firstOfNextMonth = isoDay(new Date(today.getFullYear(), today.getMonth() + 1, 1));
  const contractEnd = findEvent(options, "contract.end");
  return {
    title: kind === "date" ? "Send invoices for {period}" : contractEnd?.event.title_before ?? "",
    note: null,
    kind,
    start_date: firstOfNextMonth,
    every: 1,
    unit: "month",
    event: "contract.end",
    offset: 2,
    offset_unit: "week",
    before: true,
    client_id: null,
    paused: false,
  };
}

/** The title the composer suggests for a rule, until the user writes their own. */
export function suggestedTitle(rule: TaskRule, options: RuleOptions | null): string {
  if (rule.kind === "date") return "Send invoices for {period}";
  const found = findEvent(options, rule.event);
  if (!found) return "";
  const { event } = found;
  return rule.before || (rule.offset === 0 && !event.state) ? event.title_before ?? event.title_after : event.title_after;
}
