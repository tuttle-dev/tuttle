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

export interface CashFlowBucket {
  month: string;
  label: string;
  year: number;
  inflow_invoiced: number;
  inflow_planned: number;
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
}

type SeriesKey = "inflow_invoiced" | "inflow_planned" | "outflow" | "balance";

interface SeriesDef {
  key: SeriesKey;
  name: string;
  color: string;
  opacity: number;
  hint: string;
}

const SERIES: SeriesDef[] = [
  {
    key: "inflow_invoiced",
    name: "Invoiced",
    color: "var(--color-status-warning)",
    opacity: 1,
    hint: "Unpaid sent invoices placed by due date",
  },
  {
    key: "inflow_planned",
    name: "Planned",
    color: "var(--color-status-info)",
    opacity: 0.5,
    hint: "Scheduled calendar work shifted by payment terms",
  },
  {
    key: "outflow",
    name: "Outflows",
    color: "var(--color-status-danger)",
    opacity: 0.85,
    hint: "Fixed recurring expenses",
  },
  {
    key: "balance",
    name: "Running Balance",
    color: "var(--color-accent)",
    opacity: 1,
    hint: "Cumulative cash balance projection",
  },
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
  const netCashFlow = data?.net_cash_flow ?? 0;
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
                color: isPositive ? "var(--color-status-success)" : "var(--color-status-danger)",
              }}
            >
              {isPositive ? "+" : "−"}
              {fmtFull(Math.abs(netCashFlow))}
            </span>
            <span className="text-[11px] text-tertiary">{windowLabel}</span>
            <span
              className="text-[11px] px-1.5 py-0.5 rounded font-medium"
              style={{
                backgroundColor: isPositive
                  ? "rgba(21, 128, 61, 0.12)"
                  : "rgba(220, 38, 38, 0.12)",
                color: isPositive
                  ? "var(--color-status-success)"
                  : "var(--color-status-danger)",
              }}
            >
              {isPositive ? "Net Positive" : "Net Deficit"}
            </span>
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
              data={buckets}
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
                content={(props) => <CashFlowTooltip {...props} fmt={fmtFull} />}
              />

              {visible.includes("inflow_invoiced") && (
                <Bar
                  dataKey="inflow_invoiced"
                  name="Invoiced"
                  stackId="inflow"
                  fill="var(--color-status-warning)"
                  radius={!visible.includes("inflow_planned") ? [3, 3, 0, 0] : [0, 0, 0, 0]}
                  maxBarSize={36}
                  isAnimationActive={false}
                />
              )}
              {visible.includes("inflow_planned") && (
                <Bar
                  dataKey="inflow_planned"
                  name="Planned"
                  stackId="inflow"
                  fill="var(--color-status-info)"
                  fillOpacity={0.5}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={36}
                  isAnimationActive={false}
                />
              )}
              {visible.includes("outflow") && (
                <Bar
                  dataKey="outflow"
                  name="Outflows"
                  stackId="outflow"
                  fill="var(--color-status-danger)"
                  fillOpacity={0.85}
                  radius={[3, 3, 0, 0]}
                  maxBarSize={36}
                  isAnimationActive={false}
                />
              )}
              {visible.includes("balance") && (
                <Line
                  type="monotone"
                  dataKey="balance"
                  name="Running Balance"
                  stroke="var(--color-accent)"
                  strokeWidth={2}
                  dot={{
                    r: 3,
                    fill: "var(--color-accent)",
                    stroke: "var(--color-bg-card)",
                    strokeWidth: 1.5,
                  }}
                  activeDot={{ r: 5, fill: "var(--color-accent)" }}
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
              <span
                className="w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ background: s.color, opacity: on ? s.opacity : 0.2 }}
              />
              {s.name}
              <span className="tabular-nums text-tertiary">
                {s.key === "balance" && subtotal !== 0 && (subtotal > 0 ? "+" : "−")}
                {fmtCompact(Math.abs(subtotal))}
              </span>
            </button>
          );
        })}
      </div>
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

  return (
    <div className="rounded-lg border border-border bg-bg-card px-3 py-2 text-xs shadow-lg space-y-1.5 min-w-[200px]">
      <div className="flex items-center justify-between text-[11px] text-tertiary pb-1 border-b border-border-subtle">
        <span className="font-medium text-secondary">
          {row.label} {row.year}
        </span>
        {row.is_current && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-overlay font-medium text-primary">
            Current Month
          </span>
        )}
      </div>

      <div className="space-y-1 pt-0.5">
        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-secondary">
            <span
              className="w-2 h-2 rounded-sm shrink-0"
              style={{ background: "var(--color-status-warning)" }}
            />
            Invoiced Inflow
          </span>
          <span className="tabular-nums font-mono text-secondary">+{fmt(row.inflow_invoiced)}</span>
        </div>

        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-secondary">
            <span
              className="w-2 h-2 rounded-sm shrink-0"
              style={{ background: "var(--color-status-info)", opacity: 0.6 }}
            />
            Planned Inflow
          </span>
          <span className="tabular-nums font-mono text-secondary">+{fmt(row.inflow_planned)}</span>
        </div>

        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-secondary">
            <span
              className="w-2 h-2 rounded-sm shrink-0"
              style={{ background: "var(--color-status-danger)", opacity: 0.85 }}
            />
            Outflows
          </span>
          <span className="tabular-nums font-mono" style={{ color: "var(--color-status-danger)" }}>
            {row.outflow > 0 ? "−" : ""}
            {fmt(row.outflow)}
          </span>
        </div>
      </div>

      <div className="pt-1.5 border-t border-border-subtle space-y-1">
        <div className="flex items-center justify-between gap-4 font-medium">
          <span className="text-secondary">Monthly Net</span>
          <span
            className="tabular-nums font-mono"
            style={{
              color: row.net >= 0 ? "var(--color-status-success)" : "var(--color-status-danger)",
            }}
          >
            {row.net >= 0 ? "+" : "−"}
            {fmt(Math.abs(row.net))}
          </span>
        </div>

        <div className="flex items-center justify-between gap-4 font-medium">
          <span className="flex items-center gap-1.5 text-secondary">
            <span className="w-2 h-0.5 rounded-full shrink-0" style={{ background: "var(--color-accent)" }} />
            Running Balance
          </span>
          <span
            className="tabular-nums font-mono font-semibold"
            style={{ color: "var(--color-accent)" }}
          >
            {row.balance < 0 ? "−" : ""}
            {fmt(Math.abs(row.balance))}
          </span>
        </div>
      </div>
    </div>
  );
}
