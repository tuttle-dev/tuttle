import { useState, type ReactNode } from "react";
import { Trash2 } from "lucide-react";

/** Padding and width shared by entity detail panes and their edit forms, so toggling Edit doesn't shift content. */
export const DETAIL_PANE = "p-6 max-w-2xl";

/*
 * Header of an entity detail pane or edit form. Actions go on the right in the
 * order Complete → Duplicate → Edit → delete, and wrap below the title when
 * the pane is too narrow for both.
 */
export function DetailHeader({ avatar, title, subtitle, badges, actions }: {
  avatar?: ReactNode;
  title: string;
  subtitle?: string;
  badges?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start gap-x-4 gap-y-3">
      <div className="flex-[1_1_12rem] min-w-0 flex items-center gap-3">
        {avatar != null && (
          <div className="w-10 h-10 rounded-full bg-bg-card flex items-center justify-center text-sm font-semibold text-secondary shrink-0">
            {avatar}
          </div>
        )}
        <div className="min-w-0">
          <h1 className="text-lg font-semibold leading-snug break-words">{title}</h1>
          {(subtitle || badges) && (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1">
              {subtitle && <span className="text-sm text-secondary">{subtitle}</span>}
              {badges}
            </div>
          )}
        </div>
      </div>
      {actions && (
        <div className={`ml-auto flex flex-wrap items-center gap-1.5 ${avatar != null ? "mt-1.5" : ""}`}>{actions}</div>
      )}
    </div>
  );
}

const ACTION_BASE = "flex items-center gap-1.5 h-7 px-2.5 rounded-md text-xs font-medium border transition-colors";
const ACTION_SECONDARY = `${ACTION_BASE} text-secondary hover:text-primary border-border-subtle hover:bg-bg-hover`;

export function DetailAction({ icon, label, onClick, title }: {
  icon?: ReactNode; label: string; onClick: () => void; title?: string;
}) {
  return (
    <button type="button" onClick={onClick} title={title} className={ACTION_SECONDARY}>
      {icon}{label}
    </button>
  );
}

/** Primary submit button of an edit form. */
export function DetailSubmit({ label, disabled }: { label: string; disabled?: boolean }) {
  return (
    <button type="submit" disabled={disabled}
      className={`${ACTION_BASE} border-accent bg-accent text-white hover:bg-accent/90 disabled:opacity-40`}>
      {label}
    </button>
  );
}

/** Delete icon that asks for confirmation inline. Key it by entity id so a pending confirmation resets on selection change. */
export function DetailDeleteAction({ label, onDelete }: { label: string; onDelete: () => void }) {
  const [confirming, setConfirming] = useState(false);
  if (!confirming) {
    return (
      <button type="button" onClick={() => setConfirming(true)} title={label} aria-label={label}
        className="h-7 w-7 flex items-center justify-center rounded-md border border-border-subtle text-secondary hover:text-status-danger hover:border-status-danger/30 hover:bg-status-danger/10 transition-colors">
        <Trash2 size={14} />
      </button>
    );
  }
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-status-danger">Delete permanently?</span>
      <button type="button" onClick={() => { setConfirming(false); onDelete(); }}
        className={`${ACTION_BASE} border-red-500 bg-red-500 text-white hover:bg-red-600`}>
        Delete
      </button>
      <button type="button" onClick={() => setConfirming(false)} className={ACTION_SECONDARY}>
        Keep
      </button>
    </div>
  );
}
