import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar, CartesianGrid, ComposedChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { rpc } from "../../api/rpc";

type Granularity = "week" | "month" | "year";
type SeriesKey = "received" | "invoiced" | "planned";

interface Bucket {
  bucket: string;
  bucket_end: string;
  label: string;
  year: number;
  received: number;
  invoiced: number;
  planned: number;
  invoice_count: number;
  hours: number;
  total: number;
  is_current: boolean;
  is_future: boolean;
  is_year_start: boolean;
}

interface RevenueSeries {
  granularity: Granularity;
  offset: number;
  currency: string;
  window_start: string;
  window_end: string;
  buckets: Bucket[];
  total: number;
  has_earlier: boolean;
  has_later: boolean;
}

// Planned revenue is drawn translucent: it is an estimate, not money in hand.
const SERIES: { key: SeriesKey; name: string; color: string; opacity: number; hint: string }[] = [
  { key: "received", name: "Received", color: "var(--color-status-success)", opacity: 1, hint: "Paid invoices" },
  { key: "invoiced", name: "Invoiced", color: "var(--color-status-warning)", opacity: 1, hint: "Invoiced, not yet paid" },
  { key: "planned", name: "Planned", color: "var(--color-status-info)", opacity: 0.45, hint: "Tracked or scheduled work, not yet invoiced" },
];

const GRANULARITIES: { key: Granularity; name: string }[] = [
  { key: "week", name: "Week" },
  { key: "month", name: "Month" },
  { key: "year", name: "Year" },
];

// The band layer and the year row are plain DOM, positioned to line up with
// the chart's plot area — so the axis width and right margin are fixed here
// rather than left to Recharts' defaults.
const Y_AXIS_WIDTH = 60;
const RIGHT_MARGIN = 8;
const X_AXIS_HEIGHT = 28;

export function RevenueChart() {
  const [granularity, setGranularity] = useState<Granularity>("month");
  const [offset, setOffset] = useState(0);
  const [visible, setVisible] = useState<SeriesKey[]>(["received", "invoiced", "planned"]);
  const [data, setData] = useState<RevenueSeries | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let stale = false;
    setLoading(true);
    rpc<RevenueSeries>("dashboard.get_revenue_series", { granularity, offset }).then((res) => {
      if (stale) return;
      if (res.ok && res.data) setData(res.data);
      setLoading(false);
    });
    return () => { stale = true; };
  }, [granularity, offset]);

  function changeGranularity(next: Granularity) {
    setGranularity(next);
    setOffset(0);
  }

  // Clicking a series isolates it; clicking the isolated one restores all.
  // Cmd/Ctrl-click adds or removes a single series instead.
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
    (v: number) => new Intl.NumberFormat(undefined, {
      style: "currency", currency, notation: "compact", maximumFractionDigits: 1,
    }).format(v),
    [currency],
  );
  const fmtFull = useCallback(
    (v: number) => new Intl.NumberFormat(undefined, {
      style: "currency", currency, maximumFractionDigits: 0,
    }).format(v),
    [currency],
  );

  const buckets = data?.buckets ?? [];
  const activeSeries = useMemo(() => SERIES.filter((s) => visible.includes(s.key)), [visible]);

  const rows = useMemo(
    () => buckets.map((b) => ({
      ...b,
      visibleTotal: activeSeries.reduce((sum, s) => sum + (b[s.key] || 0), 0),
    })),
    [buckets, activeSeries],
  );

  const windowTotal = rows.reduce((sum, r) => sum + r.visibleTotal, 0);

  // Which bars get a printed value, so labels stay readable as bars get denser.
  const labelled = useMemo(() => {
    const values = rows.map((r) => r.visibleTotal);
    const indices = new Set<number>();
    const step = rows.length <= 16 ? 1 : rows.length <= 32 ? 2 : 0;
    rows.forEach((row, i) => {
      if (!values[i]) return;
      const isPeak = values[i] >= (values[i - 1] ?? 0) && values[i] >= (values[i + 1] ?? 0);
      if (step ? i % step === 0 : isPeak) indices.add(i);
      if (row.is_current) indices.add(i);
    });
    return indices;
  }, [rows]);

  const yearBands = useMemo(() => {
    const bands: { year: number; count: number }[] = [];
    for (const row of rows) {
      const last = bands[bands.length - 1];
      if (last && last.year === row.year) last.count += 1;
      else bands.push({ year: row.year, count: 1 });
    }
    return bands;
  }, [rows]);

  const windowLabel = useMemo(() => {
    if (!rows.length) return "";
    const first = rows[0], last = rows[rows.length - 1];
    if (granularity === "year") return first.year === last.year ? first.label : `${first.label}–${last.label}`;
    return `${first.label} ${first.year} – ${last.label} ${last.year}`;
  }, [rows, granularity]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (granularity === "year") return;
    if (e.key === "ArrowLeft" && data?.has_earlier) { setOffset((o) => o - 1); e.preventDefault(); }
    if (e.key === "ArrowRight" && data?.has_later) { setOffset((o) => o + 1); e.preventDefault(); }
  }

  return (
    <div
      tabIndex={0}
      onKeyDown={onKeyDown}
      className="rounded-lg bg-bg-card border border-border-subtle p-4 outline-none focus-visible:border-accent"
    >
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <h2 className="text-sm font-medium text-secondary">Revenue</h2>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-semibold tabular-nums">{fmtFull(windowTotal)}</span>
            <span className="text-[11px] text-tertiary">{windowLabel}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-md overflow-hidden border border-border">
            {GRANULARITIES.map((g, i) => (
              <button
                key={g.key}
                onClick={() => changeGranularity(g.key)}
                className={`px-2.5 h-7 text-xs transition-colors ${i > 0 ? "border-l border-border" : ""}
                  ${g.key === granularity ? "bg-bg-selected text-primary" : "text-tertiary hover:text-secondary"}`}
              >
                {g.name}
              </button>
            ))}
          </div>

          {granularity !== "year" && (
            <div className="inline-flex items-center gap-1">
              <button
                onClick={() => setOffset((o) => o - 1)} disabled={!data?.has_earlier} title="Earlier (←)"
                className="flex items-center justify-center w-7 h-7 rounded-md border border-border text-tertiary
                  hover:text-secondary disabled:opacity-30 disabled:hover:text-tertiary"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                onClick={() => setOffset((o) => o + 1)} disabled={!data?.has_later} title="Later (→)"
                className="flex items-center justify-center w-7 h-7 rounded-md border border-border text-tertiary
                  hover:text-secondary disabled:opacity-30 disabled:hover:text-tertiary"
              >
                <ChevronRight size={14} />
              </button>
              {offset !== 0 && (
                <button onClick={() => setOffset(0)} className="px-2 h-7 text-xs rounded-md border border-border text-tertiary hover:text-secondary">
                  Now
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      <div className={`relative transition-opacity ${loading ? "opacity-60" : ""}`} style={{ height: 260 }}>
        <div
          className="absolute flex pointer-events-none"
          style={{ left: Y_AXIS_WIDTH, right: RIGHT_MARGIN, top: 0, bottom: X_AXIS_HEIGHT }}
        >
          {yearBands.map((band, i) => (
            <div
              key={`${band.year}-${i}`}
              style={{ flexGrow: band.count }}
              className={`h-full ${i % 2 === 1 ? "bg-surface-overlay" : ""} ${i > 0 ? "border-l border-dashed border-border" : ""}`}
            />
          ))}
        </div>

        <div className="relative h-full z-10">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={rows} margin={{ top: 22, right: RIGHT_MARGIN, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--color-border-subtle)" />
              <XAxis
                dataKey="bucket" height={X_AXIS_HEIGHT} axisLine={false} tickLine={false} interval={0}
                tick={(props) => <BucketTick {...props} rows={rows} dense={rows.length > 20} />}
              />
              <YAxis
                width={Y_AXIS_WIDTH} axisLine={false} tickLine={false}
                tick={{ fill: "var(--color-chart-label)", fontSize: 11 }}
                tickFormatter={(v: number) => fmtCompact(v)}
              />
              <Tooltip
                cursor={{ fill: "var(--color-surface-overlay-hover)" }}
                content={(props) => <RevenueTooltip {...props} series={activeSeries} fmt={fmtFull} granularity={granularity} />}
              />

              {activeSeries.map((s, i) => {
                const isTop = i === activeSeries.length - 1;
                return (
                  <Bar
                    key={s.key}
                    dataKey={s.key}
                    name={s.name}
                    stackId="revenue"
                    fill={s.color}
                    fillOpacity={s.opacity}
                    radius={isTop ? [3, 3, 0, 0] : [0, 0, 0, 0]}
                    isAnimationActive={false}
                  >
                    {isTop && (
                      <LabelList
                        dataKey="visibleTotal"
                        content={(props) => <ValueLabel {...props} labelled={labelled} fmt={fmtCompact} />}
                      />
                    )}
                  </Bar>
                );
              })}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {granularity !== "year" && yearBands.length > 1 && (
        <div className="flex" style={{ marginLeft: Y_AXIS_WIDTH, marginRight: RIGHT_MARGIN }}>
          {yearBands.map((band, i) => (
            <div
              key={`${band.year}-${i}`}
              style={{ flexGrow: band.count }}
              className={`text-[11px] text-tertiary text-center ${i > 0 ? "border-l border-border" : ""}`}
            >
              {band.year}
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-center gap-2 mt-3 flex-wrap">
        {SERIES.map((s) => {
          const on = visible.includes(s.key);
          const subtotal = buckets.reduce((sum, b) => sum + (b[s.key] || 0), 0);
          return (
            <button
              key={s.key}
              onClick={(e) => toggleSeries(s.key, e.metaKey || e.ctrlKey)}
              title={`${s.hint} — click to show only this, ⌘/Ctrl-click to toggle`}
              className={`flex items-center gap-1.5 px-2 h-6 rounded-md border text-[11px] transition-colors
                ${on ? "border-border bg-bg-hover text-secondary" : "border-transparent text-muted hover:text-tertiary"}`}
            >
              <span
                className="w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ background: s.color, opacity: on ? s.opacity : 0.2 }}
              />
              {s.name}
              <span className="tabular-nums text-tertiary">{fmtCompact(subtotal)}</span>
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
  rows: (Bucket & { visibleTotal: number })[];
  dense: boolean;
}

function BucketTick({ x = 0, y = 0, payload, rows, dense }: TickProps) {
  const row = rows[payload?.index ?? -1];
  if (!row) return null;
  if (dense && !row.is_current && (payload?.index ?? 0) % 2 === 1) return null;
  return (
    <text
      x={x} y={y + 14} textAnchor="middle"
      fill={row.is_current ? "var(--color-primary)" : "var(--color-chart-label)"}
      fontSize={11} fontWeight={row.is_current ? 600 : 400}
    >
      {row.label}
    </text>
  );
}

interface ValueLabelProps {
  x?: number | string;
  y?: number | string;
  width?: number | string;
  value?: number | string;
  index?: number;
  labelled: Set<number>;
  fmt: (v: number) => string;
}

function ValueLabel({ x, y, width, value, index, labelled, fmt }: ValueLabelProps) {
  const amount = Number(value ?? 0);
  if (!amount || index === undefined || !labelled.has(index)) return null;
  return (
    <text
      x={Number(x) + Number(width) / 2} y={Number(y) - 6} textAnchor="middle"
      fill="var(--color-secondary)" fontSize={10} fontWeight={500}
    >
      {fmt(amount)}
    </text>
  );
}

/** "Jun 1 – 7", parsed as local dates so the day never shifts by one. */
function dayRange(startISO: string, endISO: string): string {
  const toLocal = (iso: string) => {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  };
  const start = toLocal(startISO), end = toLocal(endISO);
  const withMonth = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
  const dayOnly = new Intl.DateTimeFormat(undefined, { day: "numeric" });
  const endLabel = start.getMonth() === end.getMonth() ? dayOnly.format(end) : withMonth.format(end);
  return `${withMonth.format(start)} – ${endLabel}`;
}

interface TooltipProps {
  active?: boolean;
  payload?: { payload?: unknown }[];
  series: typeof SERIES;
  fmt: (v: number) => string;
  granularity: Granularity;
}

function RevenueTooltip({ active, payload, series, fmt, granularity }: TooltipProps) {
  const row = payload?.[0]?.payload as (Bucket & { visibleTotal: number }) | undefined;
  if (!active || !row) return null;
  // A week number alone doesn't say which days it covers; a month or year label does.
  const range = granularity === "week"
    ? `${row.label} · ${dayRange(row.bucket, row.bucket_end)}`
    : granularity === "year"
      ? row.label
      : `${row.label} ${row.year}`;

  return (
    <div className="rounded-lg border border-border bg-bg-card px-3 py-2 text-xs shadow-lg">
      <div className="text-[11px] text-tertiary mb-1">{range}</div>
      {series.map((s) => (
        <div key={s.key} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5" style={{ color: s.color }}>
            <span className="w-2 h-2 rounded-sm" style={{ background: s.color, opacity: s.opacity }} />
            {s.name}
          </span>
          <span className="tabular-nums">{fmt(row[s.key] || 0)}</span>
        </div>
      ))}
      <div className="flex items-center justify-between gap-4 mt-1 pt-1 border-t border-border-subtle font-medium">
        <span>Total</span>
        <span className="tabular-nums">{fmt(row.visibleTotal)}</span>
      </div>
      {(row.hours > 0 || row.invoice_count > 0) && (
        <div className="text-[11px] text-tertiary mt-1">
          {row.hours > 0 && `${row.hours.toFixed(1)}h uninvoiced`}
          {row.hours > 0 && row.invoice_count > 0 && " · "}
          {row.invoice_count > 0 && `${row.invoice_count} invoice${row.invoice_count > 1 ? "s" : ""}`}
        </div>
      )}
    </div>
  );
}
