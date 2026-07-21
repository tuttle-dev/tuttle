import { useEffect, useState, useCallback } from "react";
import { Wallet, BarChart3 } from "lucide-react";
import { rpc } from "../../api/rpc";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import type { Entity } from "../../api/types";
import { num } from "../../api/entity";

function fmt(value: number, currency = "EUR"): string {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
  } catch { return `${currency} ${value.toFixed(0)}`; }
}

type SalaryData = {
  conservative: number;
  optimistic: number;
  monthlyExpenses: number;
  incomeTaxReserve: number;
  vatReserve: number;
  currency: string;
};

export function SalaryView() {
  const [salary, setSalary] = useState<SalaryData | null>(null);
  const [target, setTarget] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [countrySupported, setCountrySupported] = useState(true);
  const [taxCountry, setTaxCountry] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    const res = await rpc<Entity>("salary.get_effective_salary");
    if (res.ok && res.data) {
      const d = res.data as Entity;
      const sal = d.salary as Entity | undefined;
      const cur = (d.currency as string) || "EUR";
      setCountrySupported(d.country_supported !== false);
      setTaxCountry((d.country as string) || "");
      if (sal) {
        const con = num(sal, "conservative_monthly");
        const opt = num(sal, "optimistic_monthly");
        setSalary({
          conservative: con,
          optimistic: opt,
          monthlyExpenses: num(sal, "monthly_expenses"),
          incomeTaxReserve: num(sal, "income_tax_reserve_monthly"),
          vatReserve: num(sal, "vat_reserve_monthly"),
          currency: cur,
        });
        if (target === null) setTarget(con);
      }
    }
    setLoading(false);
  }

  if (loading) return <div className="flex items-center justify-center h-full text-secondary">Loading salary data…</div>;

  if (!salary) {
    return (
      <EmptyStateIntro icon={Wallet} description="Your effective salary is what remains after taxes and business expenses — your actual take-home as a freelancer." />
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold">Effective Salary</h1>
        <p className="text-sm text-muted mt-1">How much can you safely pay yourself each month?</p>
      </div>

      <SalaryDial salary={salary} target={target!} onTargetChange={setTarget} />
      <MonthlyBreakdown salary={salary} countrySupported={countrySupported} taxCountry={taxCountry} />
    </div>
  );
}

function SalaryDial({ salary, target, onTargetChange }: {
  salary: SalaryData; target: number; onTargetChange: (v: number) => void;
}) {
  const { conservative, optimistic, currency } = salary;
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
            background: `linear-gradient(to right, #30D158 0%, #30D158 ${conPct}%, #FFD60A ${conPct}%, #FFD60A ${optPct}%, #FF453A ${optPct}%, #FF453A 100%)`,
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

function MonthlyBreakdown({ salary, countrySupported, taxCountry }: { salary: SalaryData; countrySupported: boolean; taxCountry: string }) {
  const { optimistic, vatReserve, incomeTaxReserve, monthlyExpenses, currency } = salary;
  const gross = optimistic + incomeTaxReserve + vatReserve + monthlyExpenses;
  if (gross <= 0) return null;

  const items: { label: string; amount: number; color: string; bold?: boolean; muted?: boolean }[] = [
    { label: "Gross Revenue / month", amount: gross, color: "var(--color-status-info)" },
    { label: "VAT (to remit)", amount: vatReserve, color: "var(--color-status-warning)" },
    { label: "Est. Income Tax", amount: incomeTaxReserve, color: "var(--color-status-warning)", muted: !countrySupported },
    { label: "Recurring Expenses", amount: monthlyExpenses, color: "var(--color-status-warning)" },
    { label: "= Available Salary", amount: optimistic, color: optimistic >= 0 ? "var(--color-status-success)" : "var(--color-status-danger)", bold: true },
  ];

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 size={16} className="text-secondary" />
        <h2 className="text-sm font-semibold">Monthly Breakdown</h2>
      </div>
      <div className="bg-surface-overlay rounded-lg p-4 space-y-1">
        {items.map((item, i) => {
          const pct = Math.max(Math.abs(item.amount) / gross, 0.02);
          const sign = item.amount < 0 && !item.bold ? "−" : "";
          return (
            <div key={i} className="py-1">
              <div className="flex justify-between mb-0.5">
                <span className={`text-sm ${item.bold ? "font-semibold" : ""}`}>{item.label}</span>
                <span className={`text-sm ${item.bold ? "font-semibold" : ""}`} style={{ color: item.color }}>
                  {sign}{fmt(Math.abs(item.amount), currency)}
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
