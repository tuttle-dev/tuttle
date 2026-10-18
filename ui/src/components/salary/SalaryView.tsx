import { useEffect, useState, useCallback } from "react";
import { Wallet, BarChart3 } from "lucide-react";
import { rpc } from "../../api/rpc";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { LoadError, LoadingState } from "../shared/LoadStates";
import { PageLayout } from "../shared/ToolbarButtons";
import type { Entity } from "../../api/types";
import { num, maybeNum, str, type DynamicLine } from "../../api/entity";

function fmtMonth(iso: string): string {
  const [year, month] = iso.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function fmt(value: number, currency = "EUR"): string {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
  } catch { return `${currency} ${value.toFixed(0)}`; }
}

type SalaryData = {
  // Null without tax rules: the core then gives no salary, and noTax says why.
  conservative: number | null;
  optimistic: number | null;
  grossMonthly: number;
  monthlyExpenses: number;
  dynamicLines: DynamicLine[];
  incomeTaxReserve: number | null;
  vatReserve: number;
  conversionFee: number;
  periodStart: string;
  periodEnd: string;
  currency: string;
  noTax: string;
};

export function SalaryView() {
  const [salary, setSalary] = useState<SalaryData | null>(null);
  const [target, setTarget] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    setLoadFailed(false);
    const res = await rpc<Entity>("salary.get_effective_salary");
    setLoadFailed(!res.ok);
    if (res.ok && res.data) {
      const d = res.data as Entity;
      const sal = d.salary as Entity | undefined;
      const cur = (d.currency as string) || "EUR";
      if (sal) {
        const con = maybeNum(sal, "conservative_monthly");
        const opt = maybeNum(sal, "optimistic_monthly");
        setSalary({
          conservative: con,
          optimistic: opt,
          grossMonthly: num(sal, "gross_monthly"),
          monthlyExpenses: num(sal, "monthly_expenses"),
          dynamicLines: (sal.dynamic_expenses as DynamicLine[]) || [],
          incomeTaxReserve: maybeNum(sal, "income_tax_reserve_monthly"),
          vatReserve: num(sal, "vat_reserve_monthly"),
          conversionFee: num(sal, "conversion_fee_monthly"),
          periodStart: str(sal, "period_start"),
          periodEnd: str(sal, "period_end"),
          currency: cur,
          noTax: str(sal, "tax_unavailable_reason"),
        });
        if (target === null) setTarget(con);
      }
    }
    setLoading(false);
  }

  if (loadFailed) return <PageLayout title="Salary" fallback={<LoadError what="your salary" onRetry={load} />} />;
  if (loading) return <PageLayout title="Salary" fallback={<LoadingState />} />;
  if (!salary) {
    return (
      <PageLayout title="Salary" fallback={
        <EmptyStateIntro icon={Wallet} description="Your effective salary is what remains after taxes and business expenses — your actual take-home as a freelancer." />
      } />
    );
  }

  return (
    <PageLayout title="Salary" className="grid gap-6 items-start @4xl:grid-cols-2">
      {salary.conservative === null || salary.optimistic === null ? (
        <NoSalary reason={salary.noTax} />
      ) : (
        <SalaryDial conservative={salary.conservative} optimistic={salary.optimistic} currency={salary.currency}
          target={target ?? salary.conservative} onTargetChange={setTarget} />
      )}
      <MonthlyBreakdown salary={salary} />
    </PageLayout>
  );
}

function NoSalary({ reason }: { reason: string }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Wallet size={16} className="text-secondary" />
        <h2 className="text-sm font-semibold">Monthly Salary</h2>
      </div>
      <div className="bg-surface-overlay rounded-lg px-6 py-8 text-center">
        <div className="text-4xl font-bold mb-1 text-muted">—</div>
        <div className="text-sm text-muted">{reason}</div>
      </div>
    </div>
  );
}

function SalaryDial({ conservative, optimistic, currency, target, onTargetChange }: {
  conservative: number; optimistic: number; currency: string; target: number; onTargetChange: (v: number) => void;
}) {
  const sliderMin = Math.min(conservative, 0);
  const sliderMax = Math.max(optimistic * 1.1, 1);

  const zone = useCallback((t: number) => {
    if (t <= 0) return { color: "var(--color-muted)", label: "" };
    if (t <= conservative) return { color: "var(--color-status-success)", label: "Safe zone — covered by received payments." };
    if (t <= optimistic) return { color: "var(--color-status-warning)", label: "Optimistic zone — includes invoiced amounts not yet received." };
    return { color: "var(--color-status-danger)", label: "Above the optimistic estimate — consider reducing the target." };
  }, [conservative, optimistic]);

  const z = zone(target);

  const range = sliderMax - sliderMin;
  const conPct = range > 0 ? ((conservative - sliderMin) / range) * 100 : 33;
  const optPct = range > 0 ? ((optimistic - sliderMin) / range) * 100 : 66;

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Wallet size={16} className="text-secondary" />
        <h2 className="text-sm font-semibold">Monthly Salary</h2>
      </div>
      <div className="bg-surface-overlay rounded-lg px-6 py-8 text-center">
        <div className="text-4xl font-bold mb-1" style={{ color: z.color }}>
          {fmt(target, currency)}
        </div>
        <div className="text-sm text-muted mb-6">per month</div>

        {/* Slider */}
        <input
          type="range"
          min={sliderMin}
          max={sliderMax}
          step={50}
          value={target}
          onChange={(e) => onTargetChange(Number(e.target.value))}
          className="w-full h-1.5 appearance-none rounded-full cursor-pointer"
          style={{
            background: `linear-gradient(to right, var(--color-status-success) ${conPct}%, var(--color-status-warning) ${conPct}% ${optPct}%, var(--color-status-danger) ${optPct}%)`,
            accentColor: z.color,
          }}
        />

        {/* Zone color bar (redundant with slider bg but adds clarity) */}
        <div className="flex mt-3 justify-between text-xs text-muted">
          <div>
            <div className="font-medium text-secondary">{fmt(conservative, currency)}</div>
            <div>conservative</div>
          </div>
          <div className="text-right">
            <div className="font-medium text-secondary">{fmt(optimistic, currency)}</div>
            <div>optimistic</div>
          </div>
        </div>

        {z.label && (
          <p className="text-xs mt-4" style={{ color: z.color }}>{z.label}</p>
        )}
      </div>
    </div>
  );
}

function MonthlyBreakdown({ salary }: { salary: SalaryData }) {
  const { optimistic, grossMonthly: gross, vatReserve, incomeTaxReserve, monthlyExpenses, dynamicLines, conversionFee, periodStart, periodEnd, currency } = salary;
  if (gross <= 0) return null;
  const from = periodStart ? fmtMonth(periodStart) : "";
  const to = periodEnd ? fmtMonth(periodEnd) : "";
  const period = from === to ? from : `${from} – ${to}`;

  // A null amount is a figure the core could not estimate: "—", no bar.
  const items: { label: string; amount: number | null; color: string; bold?: boolean }[] = [
    { label: "Gross Revenue / month", amount: gross, color: "var(--color-status-info)" },
    { label: "VAT (to remit)", amount: vatReserve, color: "var(--color-status-warning)" },
    { label: "Est. Income Tax", amount: incomeTaxReserve, color: "var(--color-status-warning)" },
    ...(monthlyExpenses > 0
      ? [{ label: "Fixed Recurring Expenses", amount: monthlyExpenses, color: "var(--color-status-warning)" }]
      : []),
    ...dynamicLines.map((line) => ({
      label: `${line.title} (${line.rate}%)`,
      amount: line.amount,
      color: "var(--color-status-warning)",
    })),
    ...(conversionFee > 0
      ? [{ label: "Currency Conversion", amount: conversionFee, color: "var(--color-status-warning)" }]
      : []),
    { label: "= Available Salary", amount: optimistic, color: optimistic === null ? "var(--color-muted)" : optimistic >= 0 ? "var(--color-status-success)" : "var(--color-status-danger)", bold: true },
  ];

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 size={16} className="text-secondary" />
        <h2 className="text-sm font-semibold">Monthly Breakdown</h2>
        {period && <span className="text-xs text-muted ml-auto">Average, {period}</span>}
      </div>
      <div className="bg-surface-overlay rounded-lg p-4 space-y-1">
        {items.map((item, i) => {
          const pct = item.amount === null ? 0 : Math.max(Math.abs(item.amount) / gross, 0.02);
          const shown = item.amount === null ? "—" : `${item.amount < 0 ? "−" : ""}${fmt(Math.abs(item.amount), currency)}`;
          return (
            <div key={i} className="py-1">
              <div className="flex justify-between mb-0.5">
                <span className={`text-sm ${item.bold ? "font-semibold" : ""}`}>{item.label}</span>
                <span className={`text-sm ${item.bold ? "font-semibold" : ""}`} style={{ color: item.color }}>
                  {shown}
                </span>
              </div>
              <div className={`w-full rounded-sm bg-border-subtle overflow-hidden ${item.bold ? "h-2" : "h-1.5"}`}>
                <div className="h-full rounded-sm" style={{ width: `${pct * 100}%`, backgroundColor: item.color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
