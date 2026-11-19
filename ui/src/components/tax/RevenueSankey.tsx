import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type RefObject } from "react";
import type { Entity } from "../../api/types";
import { formatAmount } from "../../api/entity";
import {
  bandPath, buildGraph, labelHeight, labelOnLeft, layout, tween, LINE, NODE_W, PLOT_H, STYLE, TOP,
  type NodeTarget, type SankeyGraph, type SankeyLayout, type SankeyNode,
} from "./sankey";

type Item = { kind: "node" | "link"; id: string };
type Hover = { item: Item; x: number; y: number };

const ANIMATION_MS = 450;

/**
 * Where the year's revenue goes, as a Sankey chart. Every node is named with
 * its amount; hovering adds its share of revenue, clicking opens where the
 * figure comes from.
 */
export function RevenueSankey({ spending, currency, onOpen }: {
  spending: Entity;
  currency: string;
  onOpen: (target: NodeTarget) => void;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const width = useWidth(wrapRef);
  const measure = useTextMeasure();
  const graph = useMemo(() => buildGraph(spending), [spending]);
  const target = useMemo(() => (width > 0 ? layout(graph, width, measure) : null), [graph, width, measure]);
  const shown = useAnimatedLayout(target, graph.key);
  const [hover, setHover] = useState<Hover | null>(null);
  const [focused, setFocused] = useState<string | null>(null);
  const hatch = "sankey-hatch-" + useId().replace(/[^\w-]/g, "");

  const fmt = (n: SankeyNode, value: number) =>
    n.kind === "shortfall" ? `−${formatAmount(value, currency)}` : formatAmount(value, currency);

  const hoverAt = (item: Item, e: React.PointerEvent) => {
    const r = wrapRef.current!.getBoundingClientRect();
    setHover({ item, x: e.clientX - r.left, y: e.clientY - r.top });
  };

  // What the hovered item touches stays lit; the rest dims.
  const lit = useMemo(() => {
    if (!hover) return null;
    const links = new Set<string>(), nodes = new Set<string>();
    for (const l of graph.links) {
      const on = hover.item.kind === "link" ? l.id === hover.item.id : l.source === hover.item.id || l.target === hover.item.id;
      if (on) { links.add(l.id); nodes.add(l.source); nodes.add(l.target); }
    }
    if (hover.item.kind === "node") nodes.add(hover.item.id);
    return { links, nodes };
  }, [hover, graph]);

  const empty = !graph.nodes.some((n) => n.value > 0);

  return (
    <div ref={wrapRef} className="relative min-w-0" onPointerLeave={() => setHover(null)}>
      {empty && <p className="text-sm text-muted">No revenue data yet.</p>}
      {shown && !empty && (
        // The width follows the card, so the card can still shrink with the window.
        <svg width="100%" height={TOP + PLOT_H + 26} className="block overflow-visible select-none"
          role="group" aria-label="Where the year's revenue goes">
          <defs>
            <pattern id={hatch} width={6} height={6} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width={6} height={6} fill="var(--color-status-danger)" fillOpacity={0.15} />
              <line x1={0} y1={0} x2={0} y2={6} stroke="var(--color-status-danger)" strokeWidth={2.5} strokeOpacity={0.7} />
            </pattern>
          </defs>

          <g>
            {graph.links.map((l) => {
              const box = shown.links[l.id];
              if (!box || box.w < 0.05) return null;
              const style = STYLE[l.kind];
              const on = lit?.links.has(l.id);
              const opacity = !lit ? style.band : on ? Math.min(style.band * 1.9, 0.85) : style.band * 0.3;
              return (
                <path key={l.id} d={bandPath(box)}
                  fill={style.hatched ? `url(#${hatch})` : style.color}
                  fillOpacity={style.hatched ? (lit && !on ? 0.3 : 1) : opacity}
                  stroke={style.dashed ? style.color : undefined}
                  strokeOpacity={style.dashed ? (!lit ? 0.55 : on ? 0.9 : 0.15) : undefined}
                  strokeDasharray={style.dashed ? "3 2" : undefined}
                  className="transition-[fill-opacity,stroke-opacity] duration-150"
                  onPointerMove={(e) => hoverAt({ kind: "link", id: l.id }, e)}
                  onPointerLeave={() => setHover(null)} />
              );
            })}
          </g>

          <g>
            {graph.nodes.map((n) => {
              const box = shown.nodes[n.id];
              if (!box || box.show < 0.01) return null;
              const style = STYLE[n.kind];
              const lines = shown.lines[n.id] ?? [n.name];
              const amount = fmt(n, box.value);
              const left = labelOnLeft(n);
              const tx = left ? box.x - 8 : box.x + NODE_W + 8;
              const top = box.labelY - labelHeight(lines) / 2;
              const mid = box.y + box.h / 2;
              const leader = n.kind !== "through" && Math.abs(box.labelY - mid) > 6;
              return (
                <g key={n.id}
                  opacity={(lit && !lit.nodes.has(n.id) ? 0.45 : 1) * box.show}
                  className={`outline-none transition-opacity duration-150 ${n.target ? "cursor-pointer" : ""}`}
                  tabIndex={0} role={n.target ? "button" : undefined} aria-label={`${n.name}: ${amount}`}
                  onPointerMove={(e) => hoverAt({ kind: "node", id: n.id }, e)}
                  onPointerLeave={() => setHover(null)}
                  onFocus={(e) => {
                    if (!e.currentTarget.matches(":focus-visible")) return;
                    setFocused(n.id);
                    setHover({ item: { kind: "node", id: n.id }, x: left ? box.x - 8 : box.x + NODE_W + 8, y: box.y + box.h });
                  }}
                  onBlur={() => { setFocused(null); setHover(null); }}
                  onClick={() => n.target && onOpen(n.target)}
                  onKeyDown={(e) => {
                    if ((e.key === "Enter" || e.key === " ") && n.target) { e.preventDefault(); onOpen(n.target); }
                  }}>
                  {/* The hit area is larger than the bar; the label's glyphs catch the pointer too. */}
                  <rect x={box.x - 6} y={box.y - 3} width={NODE_W + 12} height={Math.max(box.h, 8) + 6} fill="transparent" />
                  <rect x={box.x} y={box.y} width={NODE_W} height={box.h} rx={2}
                    fill={style.hatched ? `url(#${hatch})` : style.color} fillOpacity={style.node}
                    stroke={focused === n.id ? "var(--color-accent)" : style.dashed || style.hatched ? style.color : undefined}
                    strokeWidth={focused === n.id ? 2 : 1} strokeDasharray={style.dashed && focused !== n.id ? "3 2" : undefined} />
                  {leader && (
                    <line x1={left ? box.x - 1 : box.x + NODE_W + 1} x2={left ? box.x - 6 : box.x + NODE_W + 6}
                      y1={mid} y2={box.labelY} stroke="var(--color-border)" />
                  )}
                  {n.kind === "through" ? (
                    // Named above its column.
                    <text x={box.x} fontSize={12}>
                      <tspan x={box.x} y={TOP - 24} fill="var(--color-secondary)">{n.name}</tspan>
                      <tspan x={box.x} y={TOP - 9} fill="var(--color-primary)" fontWeight={600} className="tabular-nums">{amount}</tspan>
                    </text>
                  ) : (
                    <text x={tx} textAnchor={left ? "end" : "start"} fontSize={12}>
                      {lines.map((line, i) => (
                        <tspan key={i} x={tx} y={top + 11 + LINE * i} fill="var(--color-secondary)">{line}</tspan>
                      ))}
                      <tspan x={tx} y={top + 12 + LINE * lines.length} fontWeight={600} className="tabular-nums"
                        fill={n.kind === "shortfall" ? "var(--color-status-danger)" : "var(--color-primary)"}>
                        {amount}
                      </tspan>
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      )}
      {hover && shown && !empty && <SankeyTooltip graph={graph} hover={hover} width={shown.width} currency={currency} />}
    </div>
  );
}

function SankeyTooltip({ graph, hover, width, currency }: { graph: SankeyGraph; hover: Hover; width: number; currency: string }) {
  const nodeOf = (id: string) => graph.nodes.find((n) => n.id === id)!;
  const share = (value: number) => (graph.revenue > 0 ? `${((value / graph.revenue) * 100).toFixed(1)}% of revenue` : null);
  const money = (v: number) => formatAmount(v, currency);
  let value: string, name: string, color: string, details: (string | null)[] = [], rows: [string, number][] = [], go: string | null = null;

  if (hover.item.kind === "link") {
    const l = graph.links.find((x) => x.id === hover.item.id)!;
    const from = nodeOf(l.source), to = nodeOf(l.target);
    value = money(l.value);
    name = `${from.name} → ${to.name}`;
    color = STYLE[l.kind].color;
    if (from.value > 0) details = [`${((l.value / from.value) * 100).toFixed(1)}% of ${from.name}`];
  } else {
    const n = nodeOf(hover.item.id);
    value = n.kind === "shortfall" ? `−${money(n.value)}` : money(n.value);
    name = n.name;
    color = STYLE[n.kind].color;
    details = [n.hint ?? null, n.id === "revenue" ? null : share(n.value)];
    if (n.id === "income-tax") {
      const base = graph.nodes.find((x) => x.id === "taxbase")?.value ?? 0;
      if (base > 0) details.push(`Effective rate ${((n.value / base) * 100).toFixed(1)}% of the tax base`);
    }
    rows = n.rows ?? [];
    if (n.target) go = "section" in n.target ? "Click to show details" : `Click to open ${VIEW_NAMES[n.target.view] ?? n.target.view}`;
  }

  const flipX = hover.x > width - 300;
  return (
    <div className="absolute z-10 pointer-events-none rounded-lg border border-border bg-bg-card px-3 py-2 text-xs shadow-lg min-w-[180px] max-w-[280px]"
      style={{ left: flipX ? hover.x - 14 : hover.x + 14, top: hover.y + 14, transform: flipX ? "translateX(-100%)" : undefined }}>
      <div className="text-sm font-semibold tabular-nums text-primary">{value}</div>
      <div className="flex items-center gap-1.5 text-secondary">
        <span className="w-2.5 h-[3px] rounded-full shrink-0" style={{ background: color }} />
        {name}
      </div>
      {details.filter(Boolean).map((d) => <div key={d} className="text-muted mt-0.5">{d}</div>)}
      {rows.length > 0 && (
        <div className="mt-1.5 pt-1 border-t border-border-subtle">
          {rows.map(([label, amount]) => (
            <div key={label} className="flex justify-between gap-3 text-secondary leading-relaxed">
              <span>{label}</span><span className="tabular-nums">{money(amount)}</span>
            </div>
          ))}
        </div>
      )}
      {go && <div className="mt-1.5 text-[11px] text-muted">{go}</div>}
    </div>
  );
}

const VIEW_NAMES: Record<string, string> = {
  invoicing: "Invoicing", timetracking: "Time Tracking", contracts: "Contracts", expenses: "Expenses",
};

/** The element's width, kept up to date. */
function useWidth(ref: RefObject<HTMLElement | null>): number {
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.getBoundingClientRect().width);
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return width;
}

/** The width of a label in the chart's font. */
function useTextMeasure(): (text: string) => number {
  return useMemo(() => {
    const ctx = document.createElement("canvas").getContext("2d");
    if (!ctx) return (text: string) => text.length * 6.5;
    ctx.font = `12px ${getComputedStyle(document.body).fontFamily}`;
    return (text: string) => ctx.measureText(text).width;
  }, []);
}

/**
 * The layout to draw: *target*, reached by animation when only the figures
 * changed. A new set of nodes, a new width or reduced motion jump straight to it.
 */
function useAnimatedLayout(target: SankeyLayout | null, key: string): SankeyLayout | null {
  const [shown, setShown] = useState<{ layout: SankeyLayout; key: string } | null>(null);
  const current = useRef<{ layout: SankeyLayout; key: string } | null>(null);

  useEffect(() => {
    if (!target) return;
    const from = current.current;
    const show = (layout: SankeyLayout) => { current.current = { layout, key }; setShown(current.current); };
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!from || from.key !== key || from.layout.width !== target.width || reduced) { show(target); return; }

    let frame = 0;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min((now - start) / ANIMATION_MS, 1);
      const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      show(tween(from.layout, target, eased));
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, key]);

  // Until the effect catches up with a new set of nodes, draw the target itself.
  return shown && shown.key === key ? shown.layout : target;
}
