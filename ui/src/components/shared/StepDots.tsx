/** Wizard progress: one dot per step, the current one highlighted. */
export function StepDots({ steps, current, className = "" }: { steps: readonly string[]; current: number; className?: string }) {
  return (
    <div className={`flex items-center justify-center gap-1.5 ${className}`}>
      {steps.map((label, i) => (
        <div key={label} className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full transition-colors ${
              i === current
                ? "bg-accent"
                : i < current
                  ? "bg-accent/40"
                  : "bg-border-subtle"
            }`}
            title={label}
          />
          {i < steps.length - 1 && (
            <div className={`w-6 h-px ${i < current ? "bg-accent/40" : "bg-border-subtle"}`} />
          )}
        </div>
      ))}
    </div>
  );
}
