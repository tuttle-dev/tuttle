import type { ReactNode } from "react";

/** A titled group of fields in a form or detail pane. */
export function Section({ title, children }: { title: ReactNode; children: ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wider text-secondary mb-2">{title}</div>
      {children}
    </div>
  );
}
