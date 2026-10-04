import { ChevronDown, Search } from "lucide-react";
import { createContext, useContext, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { tint, onTint } from "./status-colors";

/* ── Layout constants ─────────────────────────────────────────────────── */

// 520px on large windows; an even split with the detail pane on small ones.
export const LIST_PANEL_WIDTH = "w-[clamp(320px,50%,520px)]";
export const LIST_ROW_PADDING = "px-4 py-3.5";

/* ── List / Detail split layout ───────────────────────────────────────── */

export function ListDetailLayout({ list, detail, footer }: {
  list: ReactNode;
  detail: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex flex-1 overflow-hidden">
      <div data-list-pane className={`${LIST_PANEL_WIDTH} shrink-0 flex flex-col overflow-hidden border-r border-border-subtle`}>
        <div className="flex-1 overflow-y-auto">{list}</div>
        {footer && (
          <div className={`${LIST_ROW_PADDING} text-xs text-tertiary border-t border-border-subtle`}>{footer}</div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto">{detail}</div>
    </div>
  );
}

/* ── Single-page layout: toolbar over a scrolling, centered body ──────── */

/** `fallback` (loading, empty or error state) replaces the body, keeping the toolbar. */
export function PageLayout({ className = "", fallback, children, ...toolbar }: Parameters<typeof Toolbar>[0] & {
  className?: string;
  fallback?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col h-full">
      <Toolbar {...toolbar} />
      {fallback ?? (
        <div className="flex-1 overflow-y-auto [scrollbar-gutter:stable]">
          <div className="@container max-w-5xl mx-auto p-6">
            <div className={className}>{children}</div>
          </div>
        </div>
      )}
    </div>
  );
}

/*
 * Toolbar — consistent top bar for all views. It is also the window's title
 * bar: empty space drags the window, controls stay clickable.
 *
 * Layout: Title | actions | ―flex― | center | ―flex― | right | Search
 *
 * - `title`   – view name (always visible, left-anchored)
 * - `actions` – primary/secondary buttons next to the title
 * - `center`  – filters or other centered content (optional)
 * - `right`   – view-mode toggle or extra controls before search (optional)
 * - `search`  – search state; omit to hide the search field
 */
export function Toolbar({ title, actions, center, right, search }: {
  title: string;
  actions?: ReactNode;
  center?: ReactNode;
  right?: ReactNode;
  search?: { value: string; onChange: (v: string) => void; placeholder?: string };
}) {
  return (
    <div className="drag-region flex items-center gap-2 px-4 h-13 shrink-0 border-b border-border-subtle">
      <h2 className="text-sm font-semibold mr-1">{title}</h2>
      {actions}
      {center ? <ToolbarCenter>{center}</ToolbarCenter> : <div className="flex-1" />}
      {right}
      {search && (
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <input type="text" placeholder={search.placeholder ?? "Search…"} value={search.value}
            onChange={(e) => search.onChange(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded-md text-sm outline-none w-44 bg-bg-card text-primary border border-border-subtle placeholder:text-muted" />
        </div>
      )}
    </div>
  );
}

export function ToolbarButtonPrimary({ icon, label, onClick }: {
  icon: ReactNode; label: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap bg-accent text-white hover:bg-accent/80 hover:shadow-sm active:scale-[0.97] transition-all">
      {icon}
      <span>{label}</span>
    </button>
  );
}

export function ToolbarButtonSecondary({ icon, label, onClick }: {
  icon: ReactNode; label: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap text-secondary hover:text-primary border border-border-subtle hover:bg-bg-hover hover:border-border active:scale-[0.97] transition-all">
      {icon}
      <span>{label}</span>
    </button>
  );
}

export function ToolbarFilterGroup<T extends string>({ options, value, onChange, colors, icons, labels }: {
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
  colors?: Record<string, string>;
  icons?: Record<string, ReactNode>;
  labels?: Record<string, ReactNode>;
}) {
  if (useContext(ToolbarNarrow))
    return <ToolbarFilterMenu options={options} value={value} onChange={onChange} colors={colors} icons={icons} labels={labels} />;
  return (
    <div className="flex items-center gap-0.5 rounded-lg bg-bg-card border border-border-subtle p-0.5">
      {options.map((opt) => {
        const active = value === opt;
        const color = colors?.[opt];
        const icon = icons?.[opt];
        return (
          <button key={opt} onClick={() => onChange(opt)}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium transition-colors"
            style={active
              ? { background: color ? tint(color, 13) : "var(--color-bg-hover)", color: color ? onTint(color) : "var(--color-primary)", border: color ? `1px solid ${tint(color, 27)}` : "1px solid var(--color-border-subtle)" }
              : { background: "transparent", color: "var(--color-tertiary)", border: "1px solid transparent" }
            }>
            {icon}{labels?.[opt] ?? opt}
          </button>
        );
      })}
    </div>
  );
}

/* ── Narrow toolbars ──────────────────────────────────────────────────── */

const ToolbarNarrow = createContext(false);

/* Center slot: fills the space between actions and right/search, and flags
   its content as narrow once it no longer fits there. */
function ToolbarCenter({ children }: { children: ReactNode }) {
  const slot = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const fullWidth = useRef(0);
  const [narrow, setNarrow] = useState(false);

  useLayoutEffect(() => {
    const update = () => {
      if (!slot.current || !content.current) return;
      if (!narrow) fullWidth.current = content.current.offsetWidth;
      setNarrow(slot.current.clientWidth < fullWidth.current);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(slot.current!);
    observer.observe(content.current!);
    return () => observer.disconnect();
  }, [narrow]);

  return (
    <div ref={slot} className="flex-1 min-w-0 flex justify-center">
      <div ref={content} className="shrink-0">
        <ToolbarNarrow.Provider value={narrow}>{children}</ToolbarNarrow.Provider>
      </div>
    </div>
  );
}

/* A filter group collapsed to its active option; clicking it opens the same
   group, stacked, as a menu. */
function ToolbarFilterMenu<T extends string>(props: Parameters<typeof ToolbarFilterGroup<T>>[0]) {
  const { value, onChange, labels } = props;
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKeyDown = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <ToolbarNarrow.Provider value={false}>
      <div ref={ref} className="relative">
        <ToolbarFilterGroup {...props} options={[value]} onChange={() => setOpen((o) => !o)}
          labels={{ ...labels, [value]: <>{labels?.[value] ?? value}<ChevronDown size={12} /></> }} />
        {open && (
          <div className="absolute top-full left-0 mt-1 z-50 min-w-full rounded-lg shadow-lg *:flex-col *:items-stretch">
            <ToolbarFilterGroup {...props} onChange={(v) => { onChange(v); setOpen(false); }} />
          </div>
        )}
      </div>
    </ToolbarNarrow.Provider>
  );
}
