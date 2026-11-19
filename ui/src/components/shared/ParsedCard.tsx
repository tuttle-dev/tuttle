import type { ReactNode } from "react";
import { Sparkles, Trash2, Check } from "lucide-react";

/**
 * The approval card of a record that AI read from a document: its name with
 * Discard and Accept, then its fields as `children`.
 */
export function ParsedCard({ title, onAccept, onDiscard, canAccept = true, acceptTitle, discardTitle, children }: {
  title: string;
  onAccept: () => void;
  onDiscard: () => void;
  /** False while the record lacks something it needs to be saved. */
  canAccept?: boolean;
  acceptTitle?: string;
  discardTitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-xl border-2 border-status-purple/40 bg-status-purple/5 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-status-purple" />
          <span className="text-sm font-semibold">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onDiscard}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs text-secondary hover:text-status-danger hover:bg-status-danger/10 transition-colors"
            title={discardTitle}>
            <Trash2 size={12} /> Discard
          </button>
          <button onClick={canAccept ? onAccept : undefined}
            disabled={!canAccept}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border transition-colors ${
              canAccept
                ? "text-status-purple hover:bg-status-purple/10 border-status-purple/30"
                : "text-muted border-border-subtle cursor-not-allowed opacity-50"
            }`}
            title={acceptTitle}>
            <Check size={12} /> Accept
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}

/** A text field on a `ParsedCard`; outlined in warning colour while required and missing. */
export function AiField({ label, value, onChange, required, missing, addressRequired }: {
  label: string; value: string; onChange: (v: string) => void;
  required?: boolean; missing?: boolean; addressRequired?: boolean;
}) {
  const showWarning = (required && missing) || addressRequired;
  return (
    <div>
      <label className="block text-xs text-status-purple/70 mb-0.5">
        {label}{required && <span className="text-status-warning ml-0.5">*</span>}
      </label>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)}
        className={`w-full px-2.5 py-1.5 rounded-md text-sm bg-bg-card text-primary outline-none
          focus:border-status-purple transition-colors placeholder:text-muted border ${
          showWarning ? "border-status-warning/60" : "border-status-purple/30"
        }`} />
    </div>
  );
}
