import { Search } from "lucide-react";
import type { ReactNode } from "react";

/* ── Layout constants ─────────────────────────────────────────────────── */

export const LIST_PANEL_WIDTH = "w-[520px]";
export const LIST_ROW_PADDING = "px-4 py-3.5";

/* ── List / Detail split layout ───────────────────────────────────────── */

export function ListDetailLayout({ list, detail, footer }: {
  list: ReactNode;
  detail: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex flex-1 overflow-hidden">
      <div className={`${LIST_PANEL_WIDTH} shrink-0 flex flex-col overflow-hidden border-r border-border-subtle`}>
        <div className="flex-1 overflow-y-auto">{list}</div>
        {footer && (
          <div className={`${LIST_ROW_PADDING} text-xs text-tertiary border-t border-border-subtle`}>{footer}</div>
        )}
      </div>
      <div className="flex-1 overflow-y-auto">{detail}</div>
    </div>
  );
}

/*
 * Toolbar — consistent top bar for all list/entity views.
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
    <div className="flex items-center gap-2 px-4 py-2 shrink-0 border-b border-border-subtle">
      <h2 className="text-sm font-semibold mr-1">{title}</h2>
      {actions}
      <div className="flex-1" />
      {center}
      {center && <div className="flex-1" />}
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
      className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-accent text-white hover:bg-accent/80 hover:shadow-sm active:scale-[0.97] transition-all">
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
      className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium text-secondary hover:text-primary border border-border-subtle hover:bg-bg-hover hover:border-border active:scale-[0.97] transition-all">
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
  labels?: Record<string, string>;
}) {
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
              ? { background: color ? `${color}22` : "var(--color-bg-hover)", color: color || "var(--color-primary)", border: color ? `1px solid ${color}44` : "1px solid var(--color-border-subtle)" }
              : { background: "transparent", color: "var(--color-tertiary)", border: "1px solid transparent" }
            }>
            {icon}{labels?.[opt] ?? opt}
          </button>
        );
      })}
    </div>
  );
}
