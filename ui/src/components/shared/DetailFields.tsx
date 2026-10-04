import type { ReactNode } from "react";

/** Grid of plain label/value fields in an entity detail pane. */
export function DetailFields({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-[repeat(auto-fill,minmax(10rem,1fr))] gap-x-6 gap-y-4">{children}</div>;
}

export function DetailField({ label, children, sub }: { label: string; children: ReactNode; sub?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] font-medium uppercase tracking-wider text-tertiary mb-0.5">{label}</div>
      <div className="text-sm break-words">
        {children}
        {sub && <span className="text-tertiary ml-1">{sub}</span>}
      </div>
    </div>
  );
}
