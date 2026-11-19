import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { CalendarRange, FileClock, FolderKanban, Gauge, Hourglass, Landmark, TriangleAlert, Wallet } from "lucide-react";
import { int, maybeNum, num, str } from "../../api/entity";
import type { Entity } from "../../api/types";
import { InfoHint } from "../shared/InfoHint";
import { INCOME_SERIES, OUTFLOW, incomeFill, translucent, type IncomeKey } from "../shared/income";
import { useNavigation } from "../shared/NavigationContext";

interface Segment { key: string; amount: number; style: React.CSSProperties }

/** Where each kind of income is in the dashboard's KPIs. */
const INCOME_FIELD: Record<IncomeKey, string> = {
  received: "received_net", invoiced: "invoiced_net", planned: "planned_revenue", contracted: "contracted_revenue",
};

const TAX = translucent(OUTFLOW, 0.85);
const EXPENSES = translucent(OUTFLOW, 0.45);

/** The dashboard's one-panel summary of the year: where the income comes from, where it goes, and what needs doing. */
export function YearOverview({ kpis }: { kpis: Entity }) {
  const { navigate } = useNavigation();
  const currency = str(kpis, "tax_currency") || "EUR";
  const money = (v: number, digits = 0) => new Intl.NumberFormat(undefined, {
    style: "currency", currency, minimumFractionDigits: digits, maximumFractionDigits: digits,
  }).format(v);

  const income = INCOME_SERIES.map((s) => ({ series: s, amount: num(kpis, INCOME_FIELD[s.key]) }));
  const incomeTotal = income.reduce((sum, i) => sum + i.amount, 0);
  const tax = maybeNum(kpis, "income_tax_reserve");
  const expenses = maybeNum(kpis, "expenses");
  const spendable = maybeNum(kpis, "spendable_income");
  const hasTax = tax !== null && expenses !== null && spendable !== null;
  // Tax and expenses can exceed the income; both bars then share the larger scale.
  const scale = hasTax ? Math.max(incomeTotal, tax + expenses) : incomeTotal;

  const outstanding = num(kpis, "outstanding_amount");
  const overdue = num(kpis, "overdue_amount");
  const overdueCount = int(kpis, "overdue_invoices");
  const notDueCount = int(kpis, "unpaid_invoices") - overdueCount;
  const ready = num(kpis, "ready_to_invoice");
  const rate = maybeNum(kpis, "effective_hourly_rate");
  const projects = int(kpis, "active_projects");
  const vat = num(kpis, "vat_reserve");

  const spendColor = spendable === null ? "var(--color-muted)"
    : spendable >= 0 ? "var(--color-status-success)" : "var(--color-status-danger)";

  return (
    <div className="rounded-lg bg-bg-card border border-border-subtle p-4">
      <div className="grid gap-x-6 gap-y-4 @3xl:grid-cols-[200px_1fr] items-start">
        <div>
          <div className="flex items-center gap-1.5 text-sm font-medium text-secondary">
            <CalendarRange size={14} className="text-tertiary" />
            {new Date().getFullYear()}
          </div>
          <div className="mt-2.5 flex items-center gap-2" style={{ color: spendColor }}>
            <Wallet size={18} strokeWidth={1.8} className="shrink-0" />
            <span className="text-xl font-semibold tabular-nums leading-tight">{spendable === null ? "—" : money(spendable)}</span>
          </div>
          <div className="mt-0.5 flex items-center gap-1 text-xs text-tertiary">
            safe to spend
            <InfoHint label="Safe to spend" text={hasTax
              ? "After income tax and expenses. Excludes VAT."
              : str(kpis, "tax_unavailable_reason") || "There is no income tax estimate."} />
          </div>
        </div>

        <div className="grid grid-cols-[1fr_auto] gap-x-3 items-center pt-1 min-w-0">
          <Bar scale={scale} segments={income.map((i) => ({ key: i.series.key, amount: i.amount, style: incomeFill(i.series) }))} />
          <span className="text-xs font-medium text-secondary tabular-nums text-right min-w-16">{money(incomeTotal)}</span>
          <Legend>
            {income.filter((i) => i.amount > 0 || i.series.key === "received").map((i) => (
              <LegendItem key={i.series.key} swatch={incomeFill(i.series)} label={i.series.name} value={money(i.amount)} hint={i.series.hint} />
            ))}
          </Legend>

          {hasTax && (
            <>
              <Bar scale={scale} segments={[
                { key: "tax", amount: tax, style: { background: TAX } },
                { key: "expenses", amount: expenses, style: { background: EXPENSES } },
                { key: "spendable", amount: Math.max(spendable, 0), style: { background: "var(--color-status-success)" } },
              ]} />
              <span />
              <Legend>
                <LegendItem swatch={{ background: TAX }} label="Income tax" value={money(tax)} />
                <LegendItem swatch={{ background: EXPENSES }} label="Expenses" value={money(expenses)}
                  hint="Recurring expenses for the whole year" />
                {spendable > 0 && <LegendItem swatch={{ background: "var(--color-status-success)" }} label="Safe to spend" />}
              </Legend>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 @3xl:grid-cols-6 gap-1 border-t border-border mt-1 pt-3">
        <Figure icon={FileClock} value={money(ready)} label="ready to invoice"
          title="Tracked work not yet invoiced"
          onClick={ready > 0 ? () => navigate("invoicing", { newInvoice: true }) : undefined} />
        <Figure icon={Hourglass} value={money(outstanding - overdue)} label={notDueCount > 0 ? `not yet due · ${notDueCount}` : "not yet due"}
          title="Sent invoices, not yet due"
          onClick={notDueCount > 0 ? () => navigate("invoicing", { invoiceStatus: "Sent" }) : undefined} />
        <Figure icon={TriangleAlert} value={money(overdue)} label={overdueCount > 0 ? `overdue · ${overdueCount}` : "overdue"}
          tone={overdue > 0 ? "var(--color-status-danger)" : undefined}
          title="Invoices past their due date"
          onClick={overdueCount > 0 ? () => navigate("invoicing", { invoiceStatus: "Overdue" }) : undefined} />
        <Figure icon={Landmark} value={money(vat)} label="VAT to remit"
          title="VAT on this year's invoices"
          onClick={() => navigate("tax")} />
        <Figure icon={Gauge} value={rate === null ? "—" : money(rate, 2)} unit={rate === null ? undefined : "/ h"} label="effective rate"
          title="Paid revenue per tracked hour" />
        <Figure icon={FolderKanban} value={String(projects)} label={projects === 1 ? "active project" : "active projects"}
          title="Projects with an active contract"
          onClick={() => navigate("projects")} />
      </div>
    </div>
  );
}

/** A bar of segments, as wide as their total is of *scale*. */
function Bar({ segments, scale }: { segments: Segment[]; scale: number }) {
  const shown = segments.filter((s) => s.amount > 0);
  const rest = scale - shown.reduce((sum, s) => sum + s.amount, 0);
  if (shown.length === 0) return <div className="h-2.5 rounded-[3px] bg-border" />;
  return (
    <div className="flex h-2.5 gap-0.5 rounded-[3px] overflow-hidden">
      {shown.map((s) => <span key={s.key} className="h-full" style={{ flexGrow: s.amount, flexBasis: 0, ...s.style }} />)}
      {rest > 0 && <span className="h-full" style={{ flexGrow: rest, flexBasis: 0 }} />}
    </div>
  );
}

function Legend({ children }: { children: ReactNode }) {
  return <div className="col-span-2 flex flex-wrap gap-x-4 gap-y-0.5 mt-1.5 mb-3 last:mb-1">{children}</div>;
}

function LegendItem({ swatch, label, value, hint }: { swatch: React.CSSProperties; label: string; value?: string; hint?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-tertiary" title={hint}>
      <span className="w-2 h-2 rounded-[2px] shrink-0" style={swatch} />
      {label}
      {value && <span className="font-medium text-secondary tabular-nums">{value}</span>}
    </span>
  );
}

function Figure({ icon: Icon, value, unit, label, title, tone, onClick }: {
  icon: LucideIcon; value: string; unit?: string; label: string; title: string; tone?: string; onClick?: () => void;
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag onClick={onClick} title={title}
      className={`flex items-start gap-2.5 px-2 py-1.5 rounded-md text-left min-w-0
        ${onClick ? "cursor-pointer hover:bg-surface-overlay-hover focus-visible:outline focus-visible:outline-accent" : ""}`}>
      <Icon size={16} strokeWidth={1.8} className="shrink-0 mt-0.5" style={{ color: tone ?? "var(--color-tertiary)" }} />
      <div className="min-w-0">
        <div className="text-sm font-medium text-secondary tabular-nums leading-snug truncate" style={tone ? { color: tone } : undefined}>
          {value}{unit && <span className="text-[11px] font-normal text-muted"> {unit}</span>}
        </div>
        <div className="text-[11px] text-muted leading-snug truncate">{label}</div>
      </div>
    </Tag>
  );
}
