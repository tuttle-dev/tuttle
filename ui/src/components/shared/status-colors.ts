// One colour per status, shared by badges, filters and board columns.
// Light and dark values live in styles/globals.css (--color-status-*).
const STATUS_COLORS: Record<string, string> = {
  lead: "var(--color-status-purple)",
  offer: "var(--color-status-warning)",
  upcoming: "var(--color-status-info)",
  active: "var(--color-status-success)",
  completed: "var(--color-status-neutral)",
  draft: "var(--color-status-neutral)",
  sent: "var(--color-status-info)",
  overdue: "var(--color-status-danger)",
  paid: "var(--color-status-success)",
  cancelled: "var(--color-status-warning)",
};

export function statusColor(status: string): string {
  return STATUS_COLORS[status.toLowerCase()] ?? "var(--color-status-neutral)";
}

/** A translucent wash of `color` (works with CSS variables, unlike hex-alpha suffixes). */
export function tint(color: string, percent: number): string {
  return `color-mix(in srgb, ${color} ${percent}%, transparent)`;
}

/** `color` pulled toward the theme's text colour, so it stays readable on its own tint. */
export function onTint(color: string): string {
  return `color-mix(in srgb, ${color} 75%, var(--color-primary))`;
}
