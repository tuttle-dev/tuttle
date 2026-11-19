import { Mail } from "lucide-react";
import { composeEmail } from "../../api/external";

/** An email address as a pill that opens a new message to it in the default mail client. `compact` is for list rows. */
export function EmailAddress({ address, compact }: { address: string; compact?: boolean }) {
  return (
    <button type="button" title={`New email to ${address}`}
      onClick={(e) => { e.stopPropagation(); composeEmail(address); }}
      className={`inline-flex items-center max-w-full min-w-0 rounded-full border border-border-subtle bg-bg-hover
        text-secondary hover:text-primary hover:border-border transition-colors
        ${compact ? "gap-1 px-1.5 -my-px text-xs" : "gap-1.5 px-2.5 py-0.5 text-sm"}`}>
      <Mail size={compact ? 11 : 13} className="shrink-0" />
      <span className="truncate">{address}</span>
    </button>
  );
}
