interface ProgressBarProps {
  progress: number;
  label?: string;
  subtitle?: string;
}

export function ProgressBar({ progress, label, subtitle }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(progress, 1));

  return (
    <div className="space-y-1">
      {(label || subtitle) && (
        <div className="flex items-baseline justify-between">
          {label && <span className="text-xs font-medium truncate">{label}</span>}
          {subtitle && <span className="text-xs text-secondary tabular-nums">{subtitle}</span>}
        </div>
      )}
      <div className="h-1 w-full rounded-full bg-bg-hover overflow-hidden">
        <div
          className="h-full rounded-full bg-progress transition-all duration-300"
          style={{ width: `${clamped * 100}%` }}
        />
      </div>
    </div>
  );
}
