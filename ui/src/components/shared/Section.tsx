import type { ReactNode } from "react";

/**
 * A titled group of fields in a form or detail pane. `data-section` names it
 * for the tour; pass `name` when the title is not plain text.
 */
export function Section({ title, name, children }: { title: ReactNode; name?: string; children: ReactNode }) {
  return (
    <div data-section={name ?? (typeof title === "string" ? title : undefined)}>
      <div className="text-xs font-semibold uppercase tracking-wider text-secondary mb-2">{title}</div>
      {children}
    </div>
  );
}
