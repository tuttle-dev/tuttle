import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { rpc } from "../../api/rpc";
import { UnconvertedNote } from "../shared/UnconvertedNote";
import { INCOME, OUTFLOW, incomeFill, translucent, type IncomeSeries } from "../shared/income";

export interface CashFlowBucket {
  month: string;
  label: string;
  year: number;
  inflow_invoiced: number;
  inflow_planned: number;
  inflow_contracted: number;
  inflow_total: number;
  outflow: number;
  net: number;
  balance: number;
  is_current: boolean;
}

export interface CashFlowSeries {
  currency: string;
  window_start: string;
  window_end: string;
  buckets: CashFlowBucket[];
  total_inflow: number;
  total_outflow: number;
  net_cash_flow: number;
  /** False without tax rules: outflows then hold no income tax, nor what is charged on taxed income. */
  tax_included: boolean;
  tax_unavailable_reason: string | null;
  left_out_with_tax: string[];
  /** Amounts left out for lack of an exchange rate, one line each. */
  unconverted: string[];
}

/** "Income tax and Pension not included: no tax model for Norway." — or "" when tax is included. */
function taxNote(data: CashFlowSeries | null): string {
  if (!data || data.tax_included !== false) return "";
  const items = ["Income tax", ...(data.left_out_with_tax ?? [])];
  const list = items.length > 1 ? `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}` : items[0];
  const reason = data.tax_unavailable_reason ?? "";
  return `${list} not included: ${reason.charAt(0).toLowerCase()}${reason.slice(1)}`;
}

type InflowKey = "inflow_invoiced" | "inflow_planned" | "inflow_contracted";
type SeriesKey = InflowKey | "outflow" | "balance";

/** Inflows look like the same kinds of income on the revenue chart. */
const INFLOWS: { key: InflowKey; income: IncomeSeries; hint: string }[] = [
  { key: "inflow_invoiced", income: INCOME.invoiced, hint: "Sent, unpaid invoices, in the month they are due" },
  { key: "inflow_planned", income: INCOME.planned, hint: "Scheduled work, in the month it should be paid" },
  { key: "inflow_contracted", income: INCOME.contracted, hint: "Agreed contract work not yet scheduled, in the month it should be paid" },
];

const OUTFLOW_FILL = translucent(OUTFLOW, 0.85);
const BALANCE_COLOR = "var(--color-accent)";

const SERIES: { key: SeriesKey; name: string; swatch: React.CSSProperties; hint: string }[] = [
  ...INFLOWS.map((f) => ({ key: f.key, name: f.income.name, swatch: incomeFill(f.income), hint: f.hint })),
  { key: "outflow", name: "Outflows", swatch: { background: OUTFLOW_FILL }, hint: "Recurring expenses, contributions and tax reserves" },
  { key: "balance", name: "Running Balance", swatch: { background: BALANCE_COLOR, height: 2 }, hint: "What the months so far add up to" },
];

const HORIZONS: { months: number; name: string }[] = [
  { months: 3, name: "3 Months" },
  { months: 6, name: "6 Months" },
  { months: 12, name: "12 Months" },
];

const Y_AXIS_WIDTH = 60;
const RIGHT_MARGIN = 8;
const X_AXIS_HEIGHT = 28;

export function CashFlowChart() {
  const [months, setMonths] = useState<number>(6);
  const [visible, setVisible] = useState<SeriesKey[]>([
    "inflow_invoiced",
    "inflow_planned",
    "inflow_contracted",
    "outflow",
    "balance",
  ]);
  const [data, setData] = useState<CashFlowSeries | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let stale = false;
    setLoading(true);
    rpc<CashFlowSeries>("dashboard.get_cash_flow", { forecast_months: months }).then((res) => {
      if (stale) return;
      if (res.ok && res.data) setData(res.data);
      setLoading(false);
    });
    return () => {
      stale = true;
    };
  }, [months]);

  function toggleSeries(key: SeriesKey, additive: boolean) {
    setVisible((current) => {
      if (additive) {
        const next = current.includes(key) ? current.filter((k) => k !== key) : [...current, key];
        return next.length ? next : current;
      }
      if (current.length === 1 && current[0] === key) return SERIES.map((s) => s.key);
      return [key];
    });
  }

  const currency = data?.currency || "EUR";
  const fmtCompact = useCallback(
    (v: number) =>
      new Intl.NumberFormat(undefined, {
        style: "currency",
        currency,
        notation: "compact",
        maximumFractionDigits: Math.abs(v) < 1000 ? 0 : 1,
      }).format(v),
    [currency],
  );
  const fmtFull = useCallback(
    (v: number) =>
      new Intl.NumberFormat(undefined, {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
      }).format(v),
    [currency],
  );

  const buckets = data?.buckets ?? [];
  // One column a month: inflows stack up from zero, outflows hang below it.
  const rows = useMemo(() => buckets.map((b) => ({ ...b, outflow_down: -b.outflow })), [buckets]);
  const shownInflows = INFLOWS.filter((f) => visible.includes(f.key));
  // The highest visible inflow carries the rounded top of the column.
  const inflowTop = shownInflows[shownInflows.length - 1]?.key;
  const netCashFlow = data?.net_cash_flow ?? 0;
  const note = taxNote(data);
  const isPositive = netCashFlow >= 0;

  const windowLabel = useMemo(() => {
    if (!buckets.length) return "";
    const first = buckets[0];
    const last = buckets[buckets.length - 1];
    if (first.year === last.year) return `${first.label} – ${last.label} ${first.year}`;
    return `${first.label} ${first.year} – ${last.label} ${last.year}`;
  }, [buckets]);

  const yearBands = useMemo(() => {
    const bands: { year: number; count: number }[] = [];
    for (const b of buckets) {
      const last = bands[bands.length - 1];
      if (last && last.year === b.year) last.count += 1;
      else bands.push({ year: b.year, count: 1 });
    }
    return bands;
  }, [buckets]);

  return (
    <div className="rounded-lg bg-bg-card border border-border-subtle p-4 outline-none">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <h2 className="text-sm font-medium text-secondary">Cash Flow Forecast</h2>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span
              className="text-xl font-semibold tabular-nums"
              style={{
                color: !data
                  ? "var(--color-tertiary)"
                  : isPositive
                  ? "var(--color-status-success)"
                  : "var(--color-status-danger)",
              }}
            >
              {!data ? (
                loading ? "…" : "—"
              ) : (
                <>
                  {isPositive ? "+" : "−"}
                  {fmtFull(Math.abs(netCashFlow))}
                </>
              )}
            </span>
            {data && <span className="text-[11px] text-tertiary">{windowLabel}</span>}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-md overflow-hidden border border-border">
            {HORIZONS.map((h, i) => (
              <button
                key={h.months}
                onClick={() => setMonths(h.months)}
                className={`px-2.5 h-7 text-xs transition-colors ${
                  i > 0 ? "border-l border-border" : ""
                } ${
                  h.months === months
                    ? "bg-bg-selected text-primary font-medium"
                    : "text-tertiary hover:text-secondary"
                }`}
              >
                {h.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div
        className={`relative transition-opacity ${loading ? "opacity-60" : ""}`}
        style={{ height: 260 }}
      >
        <div
          className="absolute flex pointer-events-none"
          style={{ left: Y_AXIS_WIDTH, right: RIGHT_MARGIN, top: 0, bottom: X_AXIS_HEIGHT }}
        >
          {yearBands.map((band, i) => (
            <div
              key={`${band.year}-${i}`}
              style={{ flexGrow: band.count }}
              className={`h-full ${i % 2 === 1 ? "bg-surface-overlay" : ""} ${
                i > 0 ? "border-l border-dashed border-border" : ""
              }`}
            />
          ))}
        </div>

        <div className="relative h-full z-10">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={rows}
              stackOffset="sign"
              margin={{ top: 22, right: RIGHT_MARGIN, left: 0, bottom: 0 }}
            >
              <CartesianGrid vertical={false} stroke="var(--color-border-subtle)" />
              <ReferenceLine y={0} stroke="var(--color-border)" strokeWidth={1.5} />
              <XAxis
                dataKey="month"
                height={X_AXIS_HEIGHT}
                axisLine={false}
                tickLine={false}
                interval={0}
                tick={(props) => <BucketTick {...props} buckets={buckets} />}
              />
              <YAxis
                width={Y_AXIS_WIDTH}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "var(--color-chart-label)", fontSize: 11 }}
                tickFormatter={(v: number) => fmtCompact(v)}
              />
              <Tooltip
                cursor={{ fill: "var(--color-surface-overlay-hover)" }}
                wrapperStyle={{ zIndex: 100, pointerEvents: "none" }}
                allowEscapeViewBox={{ x: true, y: true }}
                content={(props) => <CashFlowTooltip {...props} fmt={fmtFull} />}
              />

              {shownInflows.map((f) => (
                <Bar
                  key={f.key}
                  dataKey={f.key}
                  name={f.income.name}
                  stackId="flow"
                  fill={f.income.color}
                  fillOpacity={f.income.opacity}
                  stroke={f.income.dashed ? f.income.color : undefined}
                  strokeDasharray={f.income.dashed ? "3 2" : undefined}
                  radius={f.key === inflowTop ? [3, 3, 0, 0] : [0, 0, 0, 0]}
                  maxBarSize={48}
                  isAnimationActive={false}
                />
              ))}
              {visible.includes("outflow") && (
                <Bar
                  dataKey="outflow_down"
                  name="Outflows"
                  stackId="flow"
                  fill={OUTFLOW_FILL}
                  radius={[0, 0, 3, 3]}
                  maxBarSize={48}
                  isAnimationActive={false}
                />
              )}
              {visible.includes("balance") && (
                <Line
                  type="linear"
                  dataKey="balance"
                  name="Running Balance"
                  stroke={BALANCE_COLOR}
                  strokeWidth={2}
                  dot={{ r: 3, fill: BALANCE_COLOR, stroke: "var(--color-bg-card)", strokeWidth: 1.5 }}
                  activeDot={{ r: 5, fill: BALANCE_COLOR }}
                  isAnimationActive={false}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {yearBands.length > 1 && (
        <div className="flex" style={{ marginLeft: Y_AXIS_WIDTH, marginRight: RIGHT_MARGIN }}>
          {yearBands.map((band, i) => (
            <div
              key={`${band.year}-${i}`}
              style={{ flexGrow: band.count }}
              className={`text-[11px] text-secondary text-center ${
                i > 0 ? "border-l border-border" : ""
              }`}
            >
              {band.year}
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-center gap-2 mt-3 flex-wrap">
        {SERIES.map((s) => {
          const on = visible.includes(s.key);
          const subtotal =
            s.key === "balance"
              ? buckets.length
                ? buckets[buckets.length - 1].balance
                : 0
              : buckets.reduce((sum, b) => sum + (b[s.key] || 0), 0);
          return (
            <button
              key={s.key}
              onClick={(e) => toggleSeries(s.key, e.metaKey || e.ctrlKey)}
              title={`${s.hint} — click to isolate, ⌘/Ctrl-click to toggle`}
              className={`flex items-center gap-1.5 px-2 h-6 rounded-md border text-[11px] transition-colors ${
                on
                  ? "border-border bg-bg-hover text-secondary"
                  : "border-transparent text-muted hover:text-tertiary"
              }`}
            >
              <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={on ? s.swatch : { ...s.swatch, opacity: 0.25 }} />
              {s.name}
              <span className="tabular-nums text-tertiary">
                {s.key === "balance" && subtotal !== 0 && (subtotal > 0 ? "+" : "−")}
                {fmtCompact(Math.abs(subtotal))}
              </span>
            </button>
          );
        })}
      </div>

      {note && <p className="text-[11px] text-muted text-center mt-2">{note}</p>}
      <UnconvertedNote items={data?.unconverted} className="justify-center mt-2" />
    </div>
  );
}

interface TickProps {
  x?: number;
  y?: number;
  payload?: { index: number };
  buckets: CashFlowBucket[];
}

function BucketTick({ x = 0, y = 0, payload, buckets }: TickProps) {
  const row = buckets[payload?.index ?? -1];
  if (!row) return null;
  return (
    <text
      x={x}
      y={y + 14}
      textAnchor="middle"
      fill={row.is_current ? "var(--color-primary)" : "var(--color-chart-label)"}
      fontSize={11}
      fontWeight={row.is_current ? 600 : 400}
    >
      {row.label}
    </text>
  );
}

interface TooltipProps {
  active?: boolean;
  payload?: { payload?: unknown }[];
  fmt: (v: number) => string;
}

function CashFlowTooltip({ active, payload, fmt }: TooltipProps) {
  const row = payload?.[0]?.payload as CashFlowBucket | undefined;
  if (!active || !row) return null;
  const signed = (v: number) => `${v < 0 ? "−" : "+"}${fmt(Math.abs(v))}`;

  return (
    <div className="rounded-lg border border-border bg-bg-card px-3 py-2 text-xs shadow-lg min-w-[180px]">
      <div className="text-[11px] text-tertiary mb-1">
        {row.label} {row.year}{row.is_current && " · this month"}
      </div>
      {INFLOWS.map((f) => (
        <TooltipRow key={f.key} swatch={incomeFill(f.income)} label={f.income.name} value={`+${fmt(row[f.key])}`} />
      ))}
      <TooltipRow swatch={{ background: OUTFLOW_FILL }} label="Outflows" value={signed(-row.outflow)} />
      <div className="mt-1 pt-1 border-t border-border-subtle font-medium">
        <TooltipRow label="Net" value={signed(row.net)}
          color={row.net >= 0 ? "var(--color-status-success)" : "var(--color-status-danger)"} />
        <TooltipRow swatch={{ background: BALANCE_COLOR, height: 2 }} label="Running Balance" value={signed(row.balance)} color={BALANCE_COLOR} />
      </div>
    </div>
  );
}

function TooltipRow({ swatch, label, value, color }: { swatch?: React.CSSProperties; label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="flex items-center gap-1.5 text-secondary">
        {swatch && <span className="w-2 h-2 rounded-sm shrink-0" style={swatch} />}
        {label}
      </span>
      <span className="tabular-nums" style={color ? { color } : undefined}>{value}</span>
    </div>
  );
}
