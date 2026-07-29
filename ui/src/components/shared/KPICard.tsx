import type { LucideIcon } from "lucide-react";
import { InfoHint } from "./InfoHint";

type Props = {
  title: string;
  value: string;
  icon: LucideIcon;
  valueColor?: string;
  tooltip?: string;
};

export function KPICard({ title, value, icon: Icon, valueColor, tooltip }: Props) {
  return (
    <div className="flex flex-col gap-1.5 rounded-lg bg-bg-card border border-border-subtle p-3.5">
      <div className="flex items-center justify-between text-tertiary">
        <div className="flex items-center gap-1.5">
          <Icon size={14} strokeWidth={1.8} />
          <span className="text-xs font-semibold uppercase tracking-wider">{title}</span>
        </div>
        {tooltip && <InfoHint label={title} text={tooltip} align="right" />}
      </div>
      <span className="text-xl font-bold leading-tight truncate"
        style={valueColor ? { color: valueColor } : undefined}>
        {value || "—"}
      </span>
    </div>
  );
}
