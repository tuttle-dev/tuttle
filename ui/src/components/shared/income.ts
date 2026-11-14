import type { CSSProperties } from "react";

export type IncomeKey = "received" | "invoiced" | "planned" | "contracted";

export interface IncomeSeries { key: IncomeKey; name: string; color: string; opacity: number; dashed?: boolean; hint: string }

/**
 * The kinds of income, as the dashboard's charts and overview show them.
 * Planned is translucent: an estimate, not money in hand. Contracted is
 * fainter still and outlined, the least certain.
 */
export const INCOME_SERIES: IncomeSeries[] = [
  { key: "received", name: "Received", color: "var(--color-status-success)", opacity: 1, hint: "Paid invoices, net of VAT" },
  { key: "invoiced", name: "Invoiced", color: "var(--color-status-warning)", opacity: 1, hint: "Invoiced, not yet paid, net of VAT" },
  { key: "planned", name: "Planned", color: "var(--color-status-info)", opacity: 0.45, hint: "Tracked or scheduled work, not yet invoiced" },
  { key: "contracted", name: "Contracted", color: "var(--color-status-info)", opacity: 0.15, dashed: true, hint: "Agreed in a contract, not yet scheduled or tracked" },
];

/** Money going out: expenses and tax, as the cash flow chart's outflows. */
export const OUTFLOW = "var(--color-status-danger)";

export const INCOME: Record<IncomeKey, IncomeSeries> = Object.fromEntries(
  INCOME_SERIES.map((s) => [s.key, s]),
) as Record<IncomeKey, IncomeSeries>;

/** A colour at an opacity, as one CSS colour. */
export function translucent(color: string, opacity: number): string {
  return opacity >= 1 ? color : `color-mix(in srgb, ${color} ${Math.round(opacity * 100)}%, transparent)`;
}

/** A series' fill: its translucent colour, outlined when the series is dashed. */
export function incomeFill(s: IncomeSeries): CSSProperties {
  return {
    background: translucent(s.color, s.opacity),
    outline: s.dashed ? `1px dashed ${s.color}` : undefined,
    outlineOffset: s.dashed ? -1 : undefined,
  };
}
