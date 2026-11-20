import { useEffect, useRef, useState } from "react";
import { Split, ReceiptText, Calculator, ChevronDown } from "lucide-react";
import { rpc } from "../../api/rpc";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { InfoHint } from "../shared/InfoHint";
import { LoadError, LoadingState } from "../shared/LoadStates";
import { PageLayout } from "../shared/ToolbarButtons";
import { UnconvertedNote } from "../shared/UnconvertedNote";
import type { Entity } from "../../api/types";
import { str, num, maybeNum, bool, formatAmount } from "../../api/entity";
import { useNavigation } from "../shared/NavigationContext";
import { INCOME, incomeFill, type IncomeSeries } from "../shared/income";
import { RevenueSankey } from "./RevenueSankey";
import type { NodeTarget } from "./sankey";

function fmtPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

type Forecast = "planned" | "contracted";
type SectionId = "vat" | "tax";

export function TaxReservesView() {
  const { navigate } = useNavigation();
  const [spending, setSpending] = useState<Entity | null>(null);
  const [taxEstimate, setTaxEstimate] = useState<Entity | null>(null);
  const [months, setMonths] = useState<Entity[]>([]);
  const [vatUnconverted, setVatUnconverted] = useState<string[]>([]);
  const [currency, setCurrency] = useState("EUR");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());
  // Planned and Contracted are forecasts: switched off, the view shows the year from invoices alone.
  const [included, setIncluded] = useState<Record<Forecast, boolean>>({ planned: true, contracted: true });
  // Their amounts as last counted, for the chips while they are switched off.
  const [forecastAmounts, setForecastAmounts] = useState<Record<Forecast, number>>({ planned: 0, contracted: 0 });
  const [flash, setFlash] = useState<SectionId | null>(null);
  const sections = { vat: useRef<HTMLDivElement>(null), tax: useRef<HTMLDivElement>(null) };
  const request = useRef(0);

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

  useEffect(() => {
    const all = { planned: true, contracted: true };
    setIncluded(all);
    setForecastAmounts({ planned: 0, contracted: 0 });
    load(selectedYear, all);
  }, [selectedYear]);

  /** Load the year. A refresh, after a forecast is switched, keeps the page as it is until the figures arrive. */
  async function load(year: number, include: Record<Forecast, boolean>, refresh = false) {
    const id = ++request.current;
    if (refresh) setRefreshing(true);
    else setLoading(true);
    setLoadFailed(false);
    const params = { year, include_planned: include.planned, include_contracted: include.contracted };
    const [spRes, taxRes, vatRes] = await Promise.all([
      rpc<Entity>("tax.get_spendable_income", params),
      rpc<Entity>("tax.get_income_tax_estimate", params),
      refresh ? Promise.resolve(null) : rpc<Entity>("tax.get_monthly_vat", { year }),
    ]);
    if (id !== request.current) return;  // a later request has taken over
    setLoadFailed(!spRes.ok || !taxRes.ok || (vatRes !== null && !vatRes.ok));
    if (spRes.ok && spRes.data) {
      const data = spRes.data as Entity;
      setSpending(data);
      setCurrency(str(data, "currency") || "EUR");
      const sp = data.spending as Entity;
      setForecastAmounts((prev) => ({
        planned: include.planned ? num(sp, "planned_revenue") : prev.planned,
        contracted: include.contracted ? num(sp, "contracted_revenue") : prev.contracted,
      }));
    }
    if (taxRes.ok && taxRes.data) setTaxEstimate(taxRes.data as Entity);
    if (vatRes?.ok && vatRes.data) {
      const d = vatRes.data as Entity;
      setMonths((d.months as Entity[]) || []);
      setVatUnconverted((d.unconverted as string[]) || []);
      if (str(d, "currency")) setCurrency(str(d, "currency"));
    }
    setLoading(false);
    setRefreshing(false);
  }

  function toggle(forecast: Forecast) {
    const next = { ...included, [forecast]: !included[forecast] };
    setIncluded(next);
    load(selectedYear, next, true);
  }

  function open(target: NodeTarget) {
    if ("view" in target) {
      navigate(target.view, target.invoiceStatus ? { invoiceStatus: target.invoiceStatus } : undefined);
      return;
    }
    sections[target.section].current?.scrollIntoView({ behavior: "smooth", block: "center" });
    setFlash(null);
    requestAnimationFrame(() => setFlash(target.section));
  }

  useEffect(() => {
    if (!flash) return;
    const timer = setTimeout(() => setFlash(null), 1300);
    return () => clearTimeout(timer);
  }, [flash]);

  const yearSelector = availableYears.length > 1 && (
    <YearSelector years={availableYears} selected={selectedYear} onChange={setSelectedYear} />
  );
  if (loadFailed) {
    return <PageLayout title="Tax & Reserves" right={yearSelector}
      fallback={<LoadError what="tax data" onRetry={() => load(selectedYear, included)} />} />;
  }
  if (loading) return <PageLayout title="Tax & Reserves" right={yearSelector} fallback={<LoadingState />} />;

  const sp = spending?.spending as Entity | undefined;
  const hasAnyIncome = sp && (num(sp, "gross_revenue_ytd") > 0 || forecastAmounts.planned > 0 || forecastAmounts.contracted > 0);
  // The breakdown and the monthly VAT leave out the same invoices: name each once.
  const unconverted = [...new Set([...((sp?.unconverted as string[]) || []), ...vatUnconverted])];

  if (!hasAnyIncome && months.length === 0) {
    return <PageLayout title="Tax & Reserves" right={yearSelector}
      fallback={<EmptyStateIntro icon={Calculator} description="Tax reserves help you set aside money for income tax and VAT throughout the year, so nothing comes as a surprise." />} />;
  }

  const totalBase = sp ? num(sp, "received_gross") + num(sp, "outstanding_gross") + num(sp, "planned_revenue") + num(sp, "contracted_revenue") : 0;
  // Without tax rules the core leaves out the tax and everything after it.
  const tax = sp ? maybeNum(sp, "income_tax_reserve") : null;
  const noTax = sp ? str(sp, "tax_unavailable_reason") : "";

  return (
    <PageLayout title="Tax & Reserves" className="grid gap-6 items-start @4xl:grid-cols-2"
      right={yearSelector}>
      <Section title={`Revenue Breakdown (${selectedYear})`} icon={<Split size={16} />} className="min-w-0 @4xl:col-span-2">
        {!hasAnyIncome || !sp ? (
          <p className="text-sm text-muted">No revenue data yet.</p>
        ) : (
          <>
            <div className={`transition-opacity ${refreshing ? "opacity-60" : ""}`}>
              <RevenueSankey spending={sp} currency={currency} onOpen={open} />
            </div>
            <div className="flex flex-wrap items-center gap-1.5 mt-2">
              {(["planned", "contracted"] as const).filter((f) => forecastAmounts[f] > 0).map((f) => (
                <ForecastChip key={f} series={INCOME[f]} amount={forecastAmounts[f]} currency={currency}
                  on={included[f]} onToggle={() => toggle(f)} />
              ))}
              {totalBase > 0 && (
                <span className="ml-auto text-xs text-muted">
                  Effective reserve rate{" "}
                  <span className="text-secondary">
                    {tax === null ? "—" : `${fmtPct((num(sp, "vat_reserve") + tax) / totalBase)} of gross revenue`}
                  </span>
                </span>
              )}
            </div>
            {noTax && <p className="text-xs text-muted italic mt-2">{noTax}</p>}
          </>
        )}
        <UnconvertedNote items={unconverted} className="mt-3" />
      </Section>

      {/* Income Tax Estimate */}
      {taxEstimate && <IncomeTaxSection data={taxEstimate} currency={currency} sectionRef={sections.tax} flash={flash === "tax"} />}

      {/* Monthly VAT */}
      <Section title="Monthly VAT" icon={<ReceiptText size={16} />} sectionRef={sections.vat} flash={flash === "vat"}>
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
                  <span className="text-right font-medium" style={vat > 0 ? { color: "var(--color-status-warning)" } : undefined}>{formatAmount(vat, currency)}</span>
                </div>
              );
            })}
            <div className="flex justify-between pt-2 mt-1 border-t border-border-subtle font-semibold text-sm">
              <span>Total</span>
              <span style={months.reduce((s, m) => s + num(m, "vat_collected"), 0) > 0 ? { color: "var(--color-status-warning)" } : undefined}>
                {formatAmount(months.reduce((s, m) => s + num(m, "vat_collected"), 0), currency)}
              </span>
            </div>
          </div>
        )}
      </Section>
    </PageLayout>
  );
}

/** A forecast the breakdown counts, switched on and off like the dashboard chart's series. */
function ForecastChip({ series, amount, currency, on, onToggle }: {
  series: IncomeSeries; amount: number; currency: string; on: boolean; onToggle: () => void;
}) {
  return (
    <button onClick={onToggle} title={series.hint} aria-pressed={on}
      className={`flex items-center gap-1.5 px-2 h-6 rounded-md border text-[11px] transition-colors ${
        on ? "border-border bg-bg-hover text-secondary" : "border-transparent text-muted hover:text-tertiary"
      }`}>
      <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={on ? incomeFill(series) : { ...incomeFill(series), opacity: 0.25 }} />
      {series.name}
      <span className="tabular-nums text-tertiary">{formatAmount(amount, currency)}</span>
    </button>
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

function IncomeTaxSection({ data, currency, sectionRef, flash }: {
  data: Entity; currency: string; sectionRef?: React.Ref<HTMLDivElement>; flash?: boolean;
}) {
  const tr = data.tax_reserve as Entity | null;
  const brackets = (data.brackets as Entity[]) || [];
  const country = str(data, "country");
  const noTax = str(data, "tax_unavailable_reason");

  const received = num(data, "received_net");
  const outstanding = num(data, "outstanding_net");
  const planned = num(data, "planned_revenue");
  const contracted = num(data, "contracted_revenue");
  const deducted = num(data, "deducted_expenses");
  const incomeBasis = num(data, "income_basis");

  const parts: string[] = [];
  if (received > 0) parts.push(`${formatAmount(received, currency)} received`);
  if (outstanding > 0) parts.push(`${formatAmount(outstanding, currency)} invoiced`);
  if (planned > 0) parts.push(`${formatAmount(planned, currency)} planned`);
  if (contracted > 0) parts.push(`${formatAmount(contracted, currency)} contracted`);
  const breakdown = parts.join(" + ") + (deducted > 0 ? ` − ${formatAmount(deducted, currency)} deductible expenses` : "");

  return (
    <Section title={country ? `Income Tax Estimate (${country})` : "Income Tax Estimate"} icon={<Calculator size={16} />}
      sectionRef={sectionRef} flash={flash}
      hint="A best-guess estimate from simplified tax rules. Tuttle is not a tax advisor.">
      <div className="space-y-2">
        <SummaryRow label="Income Basis" value={formatAmount(incomeBasis, currency)} />
        {parts.length > 0 && (
          <div className="text-xs text-muted -mt-1 text-right">
            {breakdown}
          </div>
        )}
        <SummaryRow label="Estimated Income Tax" value={tr ? formatAmount(num(tr, "total_annual_reserve"), currency) : "—"} color={tr ? "var(--color-status-warning)" : undefined} bold />
        <SummaryRow label="Effective Tax Rate" value={tr ? fmtPct(num(tr, "effective_rate")) : "—"} />
        {brackets.length > 0 && (
          <div className="mt-4">
            <div className="text-[11px] font-semibold text-muted uppercase tracking-wide mb-2">Tax Brackets (marginal rates)</div>
            <div className="space-y-1">
              {brackets.map((b, i) => {
                const current = bool(b, "is_current");
                return (
                  <div
                    key={i}
                    className={`flex justify-between px-3 py-1.5 rounded-md text-sm ${current ? "bg-accent text-on-fill font-semibold" : "bg-surface-overlay text-secondary"}`}
                  >
                    <span>{str(b, "label")}</span>
                    <span>
                      {formatAmount(num(b, "start"), currency)} – {formatAmount(num(b, "end"), currency)}
                      {current && <span className="ml-2 text-xs opacity-80">◄ You are here</span>}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {noTax && (
          <p className="text-xs text-muted italic mt-3">{noTax} VAT reserves still apply.</p>
        )}
      </div>
    </Section>
  );
}

function Section({ title, icon, hint, className, sectionRef, flash, children }: {
  title: string; icon?: React.ReactNode; hint?: string; className?: string;
  /** For scrolling to the section; *flash* then rings its card once. */
  sectionRef?: React.Ref<HTMLDivElement>; flash?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={className} ref={sectionRef}>
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-secondary">{icon}</span>}
        <h2 className="text-sm font-semibold">{title}</h2>
        {hint && <InfoHint label={title} text={hint} />}
      </div>
      <div className={`bg-surface-overlay rounded-lg p-4 ${flash ? "flash-ring" : ""}`}>{children}</div>
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
