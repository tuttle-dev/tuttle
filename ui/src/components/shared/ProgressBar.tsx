import type { ReactNode } from "react";

type Tone = "accent" | "neutral" | "success" | "warning";

const TONE: Record<Tone, string> = {
  accent: "text-accent",
  neutral: "text-progress",
  success: "text-status-success",
  warning: "text-status-warning",
};

interface ProgressBarProps {
  progress: number;
  /** Share drawn hatched after `progress`, e.g. planned hours. */
  planned?: number;
  label?: string;
  /** Shown right after the label, e.g. a warning icon. */
  icon?: ReactNode;
  subtitle?: string;
  tone?: Tone;
}

export function ProgressBar({ progress, planned = 0, label, icon, subtitle, tone = "neutral" }: ProgressBarProps) {
  const done = Math.max(0, Math.min(progress, 1));
  const ahead = Math.max(0, Math.min(planned, 1 - done));

  return (
    <div className="space-y-1">
      {(label || subtitle) && (
        <div className="flex flex-wrap items-baseline justify-between gap-x-2">
          <div className="flex items-center gap-1.5 min-w-0">
            {label && <span className="text-xs font-medium truncate">{label}</span>}
            {icon}
          </div>
          {subtitle && (
            <span className={`ml-auto text-xs text-right tabular-nums ${tone === "warning" ? TONE.warning : "text-secondary"}`}>
              {subtitle}
            </span>
          )}
        </div>
      )}
      <div className={`flex h-1.5 w-full rounded-full bg-border overflow-hidden ${TONE[tone]}`}>
        <div
          className={`h-full bg-current transition-all duration-300 ${ahead > 0 ? "" : "rounded-full"}`}
          style={{ width: `${done * 100}%` }}
        />
        {ahead > 0 && (
          <div
            className="h-full opacity-50 transition-all duration-300"
            style={{
              width: `${ahead * 100}%`,
              background: "repeating-linear-gradient(45deg, currentColor 0, currentColor 2px, transparent 2px, transparent 5px)",
            }}
          />
        )}
      </div>
    </div>
  );
}
