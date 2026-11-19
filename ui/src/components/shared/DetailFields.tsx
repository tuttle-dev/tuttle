import type { ReactNode } from "react";

/** Grid of plain label/value fields in an entity detail pane. */
export function DetailFields({ children }: { children: ReactNode }) {
  return <div className="@container grid grid-cols-[repeat(auto-fill,minmax(10rem,1fr))] grid-flow-row-dense gap-x-6 gap-y-4">{children}</div>;
}

/** `wide` takes two columns when the grid has them, for a value that won't fit one (an email pill). */
export function DetailField({ label, children, sub, wide }: { label: string; children: ReactNode; sub?: string; wide?: boolean }) {
  return (
    <div className={`min-w-0 ${wide ? "@min-[21.5rem]:col-span-2" : ""}`}>
      <div className="text-[11px] font-medium uppercase tracking-wider text-tertiary mb-0.5">{label}</div>
      <div className="text-sm break-words">
        {children}
        {sub && <span className="text-tertiary ml-1">{sub}</span>}
      </div>
    </div>
  );
}
