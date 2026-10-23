import { AlertTriangle } from "lucide-react";

/**
 * One line naming the amounts a total leaves out because no exchange rate
 * could be found for them. The core names each amount; nothing shows when
 * the list is empty.
 */
export function UnconvertedNote({ items, className = "" }: { items?: string[] | null; className?: string }) {
  if (!items || items.length === 0) return null;
  const count = items.length === 1 ? "1 amount" : `${items.length} amounts`;
  return (
    <p className={`flex items-start gap-1.5 text-[11px] text-status-warning ${className}`}>
      <AlertTriangle size={11} className="shrink-0 mt-0.5" />
      <span>Leaves out {count} without an exchange rate: {items.join(", ")}.</span>
    </p>
  );
}
