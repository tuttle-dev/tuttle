import { useEffect, useState } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

/* Body placeholders for a view whose data is loading or failed to load.
 * They fill the space below the view's toolbar, like EmptyStateIntro. */

/** Quiet loading body: stays blank for fast loads, then a muted hint. */
export function LoadingState() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 400);
    return () => clearTimeout(t);
  }, []);
  return (
    <div className="flex-1 flex items-center justify-center text-sm text-muted">
      {visible && "Loading…"}
    </div>
  );
}

/** Failed load: what went wrong, what to do, and a Retry that re-runs the load. */
export function LoadError({ what, onRetry }: { what: string; onRetry: () => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 px-6 text-center">
      <AlertTriangle size={24} strokeWidth={1.5} className="text-status-warning" />
      <div>
        <div className="text-sm font-medium text-primary">Couldn't load {what}</div>
        <div className="text-xs text-tertiary mt-1">If this keeps happening, restart Tuttle.</div>
      </div>
      <button onClick={() => onRetry()}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-secondary hover:text-primary border border-border-subtle hover:bg-bg-hover hover:border-border transition-colors">
        <RotateCcw size={12} />
        Retry
      </button>
    </div>
  );
}
