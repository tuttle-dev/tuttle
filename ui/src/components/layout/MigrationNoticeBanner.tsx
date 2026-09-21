import { AlertTriangle, X } from "lucide-react";

export const MIGRATION_NOTICE_KEY = "tuttle.migrationNotice";

export function MigrationNoticeBanner({ notice, onDismiss }: { notice: string | null; onDismiss: () => void }) {
  if (!notice) return null;

  return (
    <div className="flex items-start gap-3 px-4 py-2 bg-accent/10 border-b border-accent/20 text-sm text-primary shrink-0">
      <AlertTriangle size={16} className="text-accent shrink-0 mt-0.5" />
      <span className="flex-1 whitespace-pre-line">{notice}</span>
      <button
        onClick={onDismiss}
        className="p-1 rounded hover:bg-white/10 transition-colors text-secondary"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  );
}
