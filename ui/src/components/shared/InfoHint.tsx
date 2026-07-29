import { useId } from "react";
import { Info } from "lucide-react";

type Props = {
  /** Names the thing being explained, for screen readers. */
  label: string;
  text: string;
  /** Which edge the popover lines up with; flip it when the icon sits near a viewport edge. */
  align?: "left" | "right";
};

/**
 * The app's explanatory hint: a small info icon that reveals a short note on
 * hover or keyboard focus. Use it instead of secondary body text so
 * explanations stay legible rather than shrinking to fit beside a control.
 */
export function InfoHint({ label, text, align = "left" }: Props) {
  const id = useId();
  return (
    <span className="relative group inline-flex">
      <button
        type="button"
        aria-label={`More information about ${label}`}
        aria-describedby={id}
        className="cursor-help text-tertiary hover:text-secondary rounded transition-colors focus:outline-none focus:ring-2 focus:ring-accent"
      >
        <Info size={14} strokeWidth={1.8} />
      </button>
      <span
        id={id}
        role="tooltip"
        className={`absolute bottom-full mb-2 z-50 w-56 rounded-md border border-border-subtle bg-bg-card p-3
          text-xs font-normal normal-case tracking-normal text-primary shadow-lg whitespace-normal
          opacity-0 invisible transition-all duration-150
          group-hover:opacity-100 group-hover:visible
          group-focus-within:opacity-100 group-focus-within:visible
          ${align === "right" ? "right-0" : "left-0"}`}
      >
        {text}
      </span>
    </span>
  );
}
