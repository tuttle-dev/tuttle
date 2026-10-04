import { statusColor, tint, onTint } from "./status-colors";

/* ── Status badge ──────────────────────────────────────────────────────── */

export function StatusBadge({ status, className = "" }: { status: string; className?: string }) {
  const color = statusColor(status);
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${className}`}
      style={{ background: tint(color, 10), color: onTint(color), border: `1px solid ${tint(color, 20)}` }}>
      {status}
    </span>
  );
}

/* ── Tag badge ─────────────────────────────────────────────────────────── */

export function TagBadge({ tag, className = "" }: { tag: string; className?: string }) {
  if (!tag) return null;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium bg-bg-hover text-tertiary border border-border-subtle ${className}`}>
      <span className="truncate">{tag}</span>
    </span>
  );
}
