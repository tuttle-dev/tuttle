/**
 * The revenue breakdown as a Sankey graph: where each euro of the year goes.
 *
 * Received / Invoiced / Planned / Contracted → Revenue → VAT, fixed expenses,
 * Taxable profit → deductible contributions, Tax base → income tax, expenses
 * paid from taxed income, currency conversion, Safe to Spend.
 *
 * Pure functions: the graph from the core's spending breakdown, and its layout.
 */
import type { Entity } from "../../api/types";
import { num, maybeNum, type DynamicLine } from "../../api/entity";
import { INCOME } from "../shared/income";

export type NodeKind =
  | "received" | "invoiced" | "planned" | "contracted"
  | "through" | "tax" | "expense" | "remainder" | "shortfall" | "unknown";

/** Where a node's figure comes from: a view to open, or a section of the tax view to show. */
export type NodeTarget =
  | { view: string; invoiceStatus?: string }
  | { section: "vat" | "tax" };

export interface SankeyNode {
  id: string;
  col: number;
  kind: NodeKind;
  name: string;
  value: number;
  hint?: string;
  /** Items behind the figure, e.g. the fixed expenses it sums. */
  rows?: [string, number][];
  target?: NodeTarget;
}

export interface SankeyLink { id: string; source: string; target: string; value: number; kind: NodeKind }

export interface SankeyGraph {
  nodes: SankeyNode[];
  links: SankeyLink[];
  revenue: number;
  /** Changes whenever nodes or links come or go: then the chart redraws instead of animating. */
  key: string;
}

export const COLUMNS = 5;

/** How each kind of node and band is painted: its colour, node opacity, band opacity. */
export const STYLE: Record<NodeKind, { color: string; node: number; band: number; dashed?: boolean; hatched?: boolean }> = {
  received: { color: INCOME.received.color, node: INCOME.received.opacity, band: 0.45 },
  invoiced: { color: INCOME.invoiced.color, node: INCOME.invoiced.opacity, band: 0.45 },
  planned: { color: INCOME.planned.color, node: INCOME.planned.opacity, band: 0.26 },
  contracted: { color: INCOME.contracted.color, node: INCOME.contracted.opacity, band: 0.12, dashed: true },
  through: { color: "var(--color-status-neutral)", node: 0.7, band: 0.16 },
  tax: { color: "var(--color-status-danger)", node: 1, band: 0.38 },
  expense: { color: "var(--color-status-danger)", node: 0.55, band: 0.2 },
  remainder: { color: "var(--color-status-success)", node: 1, band: 0.4 },
  shortfall: { color: "var(--color-status-danger)", node: 1, band: 0.9, hatched: true },
  unknown: { color: "var(--color-status-neutral)", node: 0, band: 0.08, dashed: true },
};

type FixedLine = { title: string; amount: number; tax_deductible: boolean };

/**
 * The graph of a spending breakdown (`tax.get_spendable_income`).
 *
 * Each node pays its outflows in order. What a node cannot pay, a single
 * Shortfall node pays: it stands left of the first expense it covers.
 */
export function buildGraph(sp: Entity): SankeyGraph {
  const nodes: SankeyNode[] = [];
  const add = (n: SankeyNode) => { nodes.push({ ...n, value: Math.max(n.value, 0) }); };
  const dyn = (sp.dynamic_expenses as DynamicLine[]) || [];
  const fixed = (sp.fixed_expenses as FixedLine[]) || [];
  const rows = (deductible: boolean): [string, number][] =>
    fixed.filter((l) => l.tax_deductible === deductible).map((l) => [l.title, Number(l.amount)]);

  const sources: SankeyNode[] = [
    { id: "received", col: 0, kind: "received", name: "Received", value: num(sp, "received_gross"),
      hint: "Paid invoices, incl. VAT", target: { view: "invoicing", invoiceStatus: "Paid" } },
    { id: "invoiced", col: 0, kind: "invoiced", name: "Invoiced", value: num(sp, "outstanding_gross"),
      hint: "Sent, not yet paid, incl. VAT", target: { view: "invoicing" } },
    { id: "planned", col: 0, kind: "planned", name: "Planned", value: num(sp, "planned_revenue"),
      hint: INCOME.planned.hint, target: { view: "timetracking" } },
    { id: "contracted", col: 0, kind: "contracted", name: "Contracted", value: num(sp, "contracted_revenue"),
      hint: INCOME.contracted.hint, target: { view: "contracts" } },
  ];
  sources.forEach(add);
  const revenue = sources.reduce((sum, n) => sum + Math.max(n.value, 0), 0);
  add({ id: "revenue", col: 1, kind: "through", name: "Revenue", value: revenue });

  // Each stage: the node money passes through, what it pays, and what it carries on.
  const stages: { from: string; pays: SankeyNode[]; carry?: SankeyNode }[] = [];
  stages.push({
    from: "revenue",
    pays: [
      { id: "vat", col: 2, kind: "tax", name: "VAT", value: num(sp, "vat_reserve"),
        hint: "Collected on invoices, owed to the tax office", target: { section: "vat" } },
      { id: "fixed", col: 2, kind: "expense", name: "Fixed expenses", value: num(sp, "business_expenses"),
        hint: "Recurring, tax-deductible", rows: rows(true), target: { view: "expenses" } },
    ],
    carry: { id: "taxable", col: 2, kind: "through", name: "Taxable profit", value: num(sp, "taxable_profit") },
  });
  stages.push({
    from: "taxable",
    pays: dyn.filter((l) => l.tax_deductible).map((l, i) => ({
      id: `deductible-${i}`, col: 3, kind: "expense" as const, name: l.title, value: Number(l.amount ?? 0),
      hint: `${Number(l.rate)}% of earned income, tax-deductible`, target: { view: "expenses" },
    })),
    carry: { id: "taxbase", col: 3, kind: "through", name: "Tax base", value: num(sp, "tax_base") },
  });

  const incomeTax = maybeNum(sp, "income_tax_reserve");
  const spendable = maybeNum(sp, "spendable");
  const fixedPostTax: SankeyNode = {
    id: "fixed-post-tax", col: 4, kind: "expense", name: "Fixed expenses, not deductible",
    value: num(sp, "fixed_expenses_post_tax"), hint: "Recurring, paid from taxed income", rows: rows(false),
    target: { view: "expenses" },
  };
  const conversion: SankeyNode = {
    id: "conversion", col: 4, kind: "expense", name: "Currency conversion", value: num(sp, "conversion_fee"),
    hint: "Bank spread on foreign-currency revenue",
  };
  if (incomeTax === null || spendable === null) {
    // Without tax rules the figures after the tax base are unknown, but for
    // the expenses that do not depend on the tax.
    const known = Math.max(fixedPostTax.value, 0) + Math.max(conversion.value, 0);
    stages.push({
      from: "taxbase",
      pays: [fixedPostTax, conversion],
      carry: { id: "unknown", col: 4, kind: "unknown", name: "Before income tax", value: num(sp, "tax_base") - known,
        hint: "Income tax and Safe to Spend are not estimated" },
    });
  } else {
    stages.push({
      from: "taxbase",
      pays: [
        { id: "income-tax", col: 4, kind: "tax", name: "Income tax", value: incomeTax,
          hint: "Estimate from simplified tax rules", target: { section: "tax" } },
        fixedPostTax,
        ...dyn.filter((l) => !l.tax_deductible).map((l, i) => ({
          id: `post-tax-${i}`, col: 4, kind: "expense" as const, name: l.title, value: Number(l.amount ?? 0),
          hint: `${Number(l.rate)}% of earned income, paid from taxed income`, target: { view: "expenses" },
        })),
        conversion,
      ],
      carry: { id: "safe", col: 4, kind: "remainder", name: "Safe to Spend", value: spendable,
        hint: "What is left after VAT, expenses and income tax" },
    });
  }

  // The money that stays runs along the top: in each column the node it
  // carries on to comes first, then what was paid out.
  for (const stage of stages) {
    if (stage.carry) add(stage.carry);
    stage.pays.forEach(add);
  }

  const links: SankeyLink[] = [];
  const link = (source: string, target: string, value: number, kind: NodeKind) =>
    links.push({ id: `${source}>${target}`, source, target, value, kind });
  for (const n of sources) link(n.id, "revenue", Math.max(n.value, 0), n.kind);

  const uncovered: { node: SankeyNode; value: number }[] = [];
  let available = revenue;
  for (const stage of stages) {
    for (const paid of stage.pays) {
      const need = Math.max(paid.value, 0);
      const covered = Math.min(need, Math.max(available, 0));
      link(stage.from, paid.id, covered, paid.kind);
      if (need - covered > 0.005) uncovered.push({ node: paid, value: need - covered });
      available -= covered;
    }
    if (stage.carry) {
      const carried = Math.max(Math.min(stage.carry.value, available), 0);
      link(stage.from, stage.carry.id, carried, stage.carry.kind);
      available = carried;
    }
  }
  if (uncovered.length > 0) {
    const total = uncovered.reduce((sum, u) => sum + u.value, 0);
    const col = Math.min(...uncovered.map((u) => u.node.col)) - 1;
    nodes.push({ id: "shortfall", col, kind: "shortfall", name: "Shortfall", value: total,
      hint: "Expenses exceed what is left" });
    for (const u of uncovered) link("shortfall", u.node.id, u.value, "shortfall");
  }

  const key = nodes.map((n) => n.id).join() + "|" + links.map((l) => l.id).join();
  return { nodes, links, revenue, key };
}

/* ---------- Layout ---------- */

export const NODE_W = 10;
const PAD = 12;
export const PLOT_H = 300;
/** Room above the plot for the names of the columns money passes through. */
export const TOP = 44;
export const LINE = 14;
const LEFT_LABELS = 104;
const RIGHT_LABELS = 200;

export interface NodeBox { x: number; y: number; h: number; value: number; show: number; labelY: number }
export interface LinkBox { x0: number; x1: number; sy: number; ty: number; w: number; value: number }
export interface SankeyLayout {
  width: number;
  nodes: Record<string, NodeBox>;
  links: Record<string, LinkBox>;
  lines: Record<string, string[]>;
}

/** The height of a label: its name's lines and the amount below them. */
export const labelHeight = (lines: string[]) => LINE * (lines.length + 1) + 2;

/** Whether a node's label stands left of it: the sources, and a shortfall whose bands leave to the right. */
export const labelOnLeft = (n: SankeyNode) => n.col === 0 || n.kind === "shortfall";

/** A name broken into at most two lines no wider than *maxWidth*. */
function wrap(text: string, maxWidth: number, measure: (s: string) => number): string[] {
  if (measure(text) <= maxWidth) return [text];
  const lines = [""];
  for (const word of text.split(" ")) {
    const last = lines[lines.length - 1];
    const joined = last ? `${last} ${word}` : word;
    if (!last || measure(joined) <= maxWidth) lines[lines.length - 1] = joined;
    else lines.push(word);
  }
  if (lines.length <= 2) return lines;
  let second = lines.slice(1).join(" ");
  while (second.length > 1 && measure(`${second}…`) > maxWidth) second = second.slice(0, -1);
  return [lines[0], `${second.trimEnd()}…`];
}

/**
 * Where everything goes at *width*: columns spread across, nodes stacked from
 * the top, each band leaving its source and reaching its target in node order.
 */
export function layout(g: SankeyGraph, width: number, measure: (s: string) => number): SankeyLayout {
  const colX = (i: number) => LEFT_LABELS + ((width - RIGHT_LABELS - NODE_W - LEFT_LABELS) * i) / (COLUMNS - 1);
  const columns = [...Array(COLUMNS)].map((_, i) => g.nodes.filter((n) => n.col === i));
  let k = Infinity;
  for (const col of columns) {
    const shown = col.filter((n) => n.value > 0);
    const total = shown.reduce((sum, n) => sum + n.value, 0);
    if (total > 0) k = Math.min(k, (PLOT_H - PAD * (shown.length - 1)) / total);
  }
  if (!Number.isFinite(k)) k = 0;

  const out: SankeyLayout = { width, nodes: {}, links: {}, lines: {} };
  for (const col of columns) {
    let y = TOP;
    for (const n of col) {
      // A tiny figure, such as a conversion fee, still gets a visible node.
      const h = n.value > 0 ? Math.max(n.value * k, 2) : 0;
      out.nodes[n.id] = { x: colX(n.col), y, h, value: n.value, show: n.value > 0 ? 1 : 0, labelY: y + h / 2 };
      if (h > 0) y += h + PAD;
    }
  }

  const order = Object.fromEntries(g.nodes.map((n, i) => [n.id, i]));
  const outOffset: Record<string, number> = {};
  const inOffset: Record<string, number> = {};
  for (const l of [...g.links].sort((a, b) => order[a.target] - order[b.target])) {
    const from = out.nodes[l.source];
    const w = l.value * k;
    out.links[l.id] = { x0: from.x + NODE_W, x1: out.nodes[l.target].x, sy: from.y + (outOffset[l.source] ?? 0), ty: 0, w, value: l.value };
    outOffset[l.source] = (outOffset[l.source] ?? 0) + w;
  }
  for (const l of [...g.links].sort((a, b) => order[a.source] - order[b.source])) {
    out.links[l.id].ty = out.nodes[l.target].y + (inOffset[l.target] ?? 0);
    inOffset[l.target] = (inOffset[l.target] ?? 0) + l.value * k;
  }

  // Labels: the nodes money passes through are named above their column, the
  // others beside their node, pushed apart where small nodes crowd together.
  const gap = colX(1) - colX(0);
  for (const n of g.nodes) {
    const maxWidth = n.col === 0 ? LEFT_LABELS - 14 : n.col === COLUMNS - 1 ? RIGHT_LABELS - 14 : gap - NODE_W - 14;
    out.lines[n.id] = n.kind === "through" ? [n.name] : wrap(n.name, maxWidth, measure);
  }
  for (const col of columns) {
    for (const side of [true, false]) {
      const labels = col
        .filter((n) => n.value > 0 && n.kind !== "through" && labelOnLeft(n) === side)
        .map((n) => ({ id: n.id, y: out.nodes[n.id].labelY, h: labelHeight(out.lines[n.id]) }));
      for (let i = 1; i < labels.length; i++) {
        labels[i].y = Math.max(labels[i].y, labels[i - 1].y + (labels[i - 1].h + labels[i].h) / 2 + 2);
      }
      const bottom = TOP + PLOT_H + 6;
      for (let i = labels.length - 1; i >= 0; i--) {
        labels[i].y = Math.min(labels[i].y, bottom);
        if (i > 0) labels[i - 1].y = Math.min(labels[i - 1].y, labels[i].y - (labels[i - 1].h + labels[i].h) / 2 - 2);
      }
      for (const l of labels) out.nodes[l.id].labelY = l.y;
    }
  }
  return out;
}

/** The band between two nodes: a ribbon of width *w* bending halfway. */
export function bandPath({ x0, x1, sy, ty, w }: LinkBox): string {
  const xm = (x0 + x1) / 2;
  const h = Math.max(w, 0.6);
  return `M${x0},${sy}C${xm},${sy} ${xm},${ty} ${x1},${ty}L${x1},${ty + h}C${xm},${ty + h} ${xm},${sy + h} ${x0},${sy + h}Z`;
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
function mix<T extends object>(a: T | undefined, b: T, t: number): T {
  const out = { ...b };
  for (const key of Object.keys(b) as (keyof T)[]) {
    const from = a?.[key] ?? b[key];
    if (typeof b[key] === "number") (out[key] as number) = lerp(from as number, b[key] as number, t);
  }
  return out;
}

/** The layout part way, *t* from 0 to 1, from *a* to *b*: for animating a change of figures. */
export function tween(a: SankeyLayout, b: SankeyLayout, t: number): SankeyLayout {
  const nodes: Record<string, NodeBox> = {};
  const links: Record<string, LinkBox> = {};
  for (const id in b.nodes) nodes[id] = mix(a.nodes[id], b.nodes[id], t);
  for (const id in b.links) links[id] = mix(a.links[id], b.links[id], t);
  return { width: b.width, nodes, links, lines: b.lines };
}
