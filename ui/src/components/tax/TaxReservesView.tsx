import { useEffect, useState } from "react";
import { BarChart3, ReceiptText, Calculator, ChevronDown } from "lucide-react";
import { rpc } from "../../api/rpc";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import type { Entity } from "../../api/types";
import { str, num, bool } from "../../api/entity";

function fmt(value: number, currency = "EUR"): string {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
  } catch { return `${currency} ${value.toFixed(0)}`; }
}

function fmtPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function TaxReservesView() {
  const [spending, setSpending] = useState<Entity | null>(null);
  const [taxEstimate, setTaxEstimate] = useState<Entity | null>(null);
  const [months, setMonths] = useState<Entity[]>([]);
  const [currency, setCurrency] = useState("EUR");
  const [loading, setLoading] = useState(true);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());

  useEffect(() => {
    rpc<number[]>("tax.get_available_years").then((res) => {
      if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
        setAvailableYears(res.data);
        if (!res.data.includes(selectedYear)) {
          setSelectedYear(res.data[0]);
        }
      } else {
        setAvailableYears([new Date().getFullYear()]);
      }
    });
  }, []);

  useEffect(() => { load(selectedYear); }, [selectedYear]);

  async function load(year: number) {
    setLoading(true);
    const params = { year };
    const [spRes, taxRes, vatRes] = await Promise.all([
      rpc<Entity>("tax.get_spendable_income", params),
      rpc<Entity>("tax.get_income_tax_estimate", params),
      rpc<Entity>("tax.get_monthly_vat", params),
    ]);
    if (spRes.ok && spRes.data) {
      setSpending(spRes.data as Entity);
      setCurrency(str(spRes.data as Entity, "currency") || "EUR");
    }
    if (taxRes.ok && taxRes.data) setTaxEstimate(taxRes.data as Entity);
    if (vatRes.ok && vatRes.data) {
      const d = vatRes.data as Entity;
      setMonths((d.months as Entity[]) || []);
      if (str(d, "currency")) setCurrency(str(d, "currency"));
    }
    setLoading(false);
  }

  if (loading) return <div className="flex items-center justify-center h-full text-secondary">Loading tax data…</div>;

  const sp = spending?.spending as Entity | undefined;
  const hasAnyIncome = sp && (num(sp, "gross_revenue_ytd") > 0 || num(sp, "planned_revenue") > 0);
  const isCurrentYear = selectedYear === new Date().getFullYear();
  const periodLabel = isCurrentYear ? "YTD" : `${selectedYear}`;

  if (!hasAnyIncome && months.length === 0) {
    return <EmptyStateIntro icon={Calculator} description="Tax reserves help you set aside money for income tax and VAT throughout the year, so nothing comes as a surprise." />;
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Tax &amp; Reserves</h1>
          <p className="text-sm text-muted mt-1">How much of your revenue can you actually spend?</p>
        </div>
        {availableYears.length > 1 && (
          <YearSelector
            years={availableYears}
            selected={selectedYear}
            onChange={setSelectedYear}
          />
        )}
      </div>

      {/* Revenue Waterfall */}
      <Section title={`Revenue Breakdown (${periodLabel})`} icon={<BarChart3 size={16} />}>
        {!hasAnyIncome ? (
          <p className="text-sm text-muted">No revenue data yet.</p>
        ) : (() => {
          const received = num(sp!, "received_gross");
          const outstanding = num(sp!, "outstanding_gross");
          const planned = num(sp!, "planned_revenue");
          const totalBase = received + outstanding + planned;
          const vat = num(sp!, "vat_reserve");
          const bizExpenses = num(sp!, "business_expenses");
          const taxableProfit = num(sp!, "taxable_profit");
          const tax = num(sp!, "income_tax_reserve");
          const spendable = num(sp!, "spendable");
          return (
            <div className="space-y-1">
              <WaterfallBar label="Received" amount={received} total={totalBase} color="var(--color-status-info)" currency={currency} />
              {outstanding > 0 && (
                <WaterfallBar label="Invoiced" amount={outstanding} total={totalBase} color="var(--color-status-info-muted, var(--color-status-info))" currency={currency} />
              )}
              {planned > 0 && (
                <WaterfallBar label="Planned" amount={planned} total={totalBase} color="var(--color-accent, #6366f1)" currency={currency} />
              )}
              <WaterfallBar label="VAT (to remit)" amount={vat} total={totalBase} color="var(--color-status-warning)" currency={currency} />
              {bizExpenses > 0 && (
                <WaterfallBar label="Business Expenses" amount={bizExpenses} total={totalBase} color="var(--color-status-warning)" currency={currency} />
              )}
              <WaterfallBar label="= Taxable Profit" amount={taxableProfit} total={totalBase} color="var(--color-status-info)" currency={currency} />
              <WaterfallBar label="Est. Income Tax + Soli" amount={tax} total={totalBase} color="var(--color-status-warning)" currency={currency} />
              <WaterfallBar label="= Safe to Spend" amount={spendable} total={totalBase} color={spendable >= 0 ? "var(--color-status-success)" : "var(--color-status-danger)"} currency={currency} bold />
              {totalBase > 0 && (
                <div className="border-t border-border-subtle mt-3 pt-3 flex justify-between text-xs text-muted">
                  <span>Effective reserve rate</span>
                  <span className="text-secondary">
                    {fmtPct((vat + tax) / totalBase)} of gross revenue
                  </span>
                </div>
              )}
            </div>
          );
        })()}
      </Section>

      {/* Monthly VAT */}
      <Section title="Monthly VAT" icon={<ReceiptText size={16} />}>
        {months.length === 0 ? (
          <p className="text-sm text-muted">No VAT data available.</p>
        ) : (
          <div>
            <div className="grid grid-cols-3 gap-2 text-[11px] font-semibold text-muted uppercase tracking-wide pb-2 border-b border-border-subtle">
              <span>Month</span><span className="text-right">Invoices</span><span className="text-right">VAT Collected</span>
            </div>
            {months.map((m, i) => {
              const vat = num(m, "vat_collected");
              return (
                <div key={i} className="grid grid-cols-3 gap-2 py-1.5 text-sm border-b border-border-subtle/50 last:border-0">
                  <span className="font-semibold">{str(m, "month")}</span>
                  <span className="text-right">{num(m, "invoice_count")}</span>
                  <span className="text-right font-medium" style={vat > 0 ? { color: "var(--color-status-warning)" } : undefined}>{fmt(vat, currency)}</span>
                </div>
              );
            })}
            <div className="flex justify-between pt-2 mt-1 border-t border-border-subtle font-semibold text-sm">
              <span>Total</span>
              <span style={months.reduce((s, m) => s + num(m, "vat_collected"), 0) > 0 ? { color: "var(--color-status-warning)" } : undefined}>
                {fmt(months.reduce((s, m) => s + num(m, "vat_collected"), 0), currency)}
              </span>
            </div>
          </div>
        )}
      </Section>

      {/* Income Tax Estimate */}
      {taxEstimate && <IncomeTaxSection data={taxEstimate} currency={currency} />}
    </div>
  );
}

function YearSelector({ years, selected, onChange }: {
  years: number[]; selected: number; onChange: (y: number) => void;
}) {
  return (
    <div className="relative">
      <select
        value={selected}
        onChange={(e) => onChange(Number(e.target.value))}
        className="appearance-none bg-surface-overlay border border-border-subtle rounded-md px-3 py-1.5 pr-8 text-sm font-medium text-primary cursor-pointer hover:bg-surface-overlay-hover transition-colors"
      >
        {years.map((y) => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>
      <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
    </div>
  );
}

function IncomeTaxSection({ data, currency }: { data: Entity; currency: string }) {
  const tr = data.tax_reserve as Entity | undefined;
  const brackets = (data.brackets as Entity[]) || [];
  const country = str(data, "country");
  const supported = data.country_supported !== false;

  const received = num(data, "received_net");
  const outstanding = num(data, "outstanding_net");
  const planned = num(data, "planned_revenue");
  const incomeBasis = num(data, "income_basis");

  const parts: string[] = [];
  if (received > 0) parts.push(`${fmt(received, currency)} received`);
  if (outstanding > 0) parts.push(`${fmt(outstanding, currency)} invoiced`);
  if (planned > 0) parts.push(`${fmt(planned, currency)} planned`);

  return (
    <Section title={`Income Tax Estimate (${country})`} icon={<Calculator size={16} />}>
      <div className="space-y-2">
        <SummaryRow label="Income Basis" value={fmt(incomeBasis, currency)} />
        {parts.length > 0 && (
          <div className="text-xs text-muted -mt-1 text-right">
            {parts.join(" + ")}
          </div>
        )}
        {supported && tr && (
          <>
            <SummaryRow label="Estimated Income Tax" value={fmt(num(tr, "estimated_annual_tax"), currency)} color="var(--color-status-warning)" />
            <SummaryRow label="Solidarity Surcharge" value={fmt(num(tr, "solidarity_surcharge"), currency)} color="var(--color-status-warning)" />
            <SummaryRow label="Total Annual Reserve" value={fmt(num(tr, "total_annual_reserve"), currency)} color="var(--color-status-warning)" bold />
            <SummaryRow label="Effective Tax Rate" value={fmtPct(num(tr, "effective_rate"))} />
          </>
        )}
        {brackets.length > 0 && (
          <div className="mt-4">
            <div className="text-[11px] font-semibold text-muted uppercase tracking-wide mb-2">Tax Brackets (marginal rates)</div>
            <div className="space-y-1">
              {brackets.map((b, i) => {
                const current = bool(b, "is_current");
                return (
                  <div
                    key={i}
                    className={`flex justify-between px-3 py-1.5 rounded-md text-sm ${current ? "bg-accent text-white font-semibold" : "bg-surface-overlay text-secondary"}`}
                  >
                    <span>{str(b, "label")}</span>
                    <span>
                      {fmt(num(b, "start"), currency)} – {fmt(num(b, "end"), currency)}
                      {current && <span className="ml-2 text-xs opacity-80">◄ You are here</span>}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {!supported && (
          <p className="text-xs text-muted italic mt-3">
            Income tax estimation is not yet available for {country}. VAT reserves are still tracked above.
          </p>
        )}
      </div>
    </Section>
  );
}

function Section({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-secondary">{icon}</span>}
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <div className="bg-surface-overlay rounded-lg p-4">{children}</div>
    </div>
  );
}

function WaterfallBar({ label, amount, total, color, currency, bold }: {
  label: string; amount: number; total: number; color: string; currency: string; bold?: boolean;
}) {
  const pct = total > 0 ? Math.max(Math.abs(amount) / total, 0.02) : 0;
  const sign = amount < 0 && !bold ? "−" : "";
  const display = Math.abs(amount);

  return (
    <div className="py-1">
      <div className="flex justify-between mb-0.5">
        <span className={`text-sm ${bold ? "font-semibold" : ""}`}>{label}</span>
        <span className={`text-sm ${bold ? "font-semibold" : ""}`} style={{ color }}>{sign}{fmt(display, currency)}</span>
      </div>
      <div className={`w-full rounded-sm bg-border-subtle overflow-hidden ${bold ? "h-2" : "h-1.5"}`}>
        <div className="h-full rounded-sm" style={{ width: `${pct * 100}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function SummaryRow({ label, value, color, bold }: { label: string; value: string; color?: string; bold?: boolean }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-secondary">{label}</span>
      <span className={bold ? "font-semibold" : ""} style={color ? { color } : undefined}>{value}</span>
    </div>
  );
}
