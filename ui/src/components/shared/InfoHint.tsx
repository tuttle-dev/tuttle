import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Info } from "lucide-react";

type Props = {
  /** Names the thing being explained, for screen readers. */
  label: string;
  text: string;
  /** Which edge the popover lines up with; flip it when the icon sits near a viewport edge. */
  align?: "left" | "right";
};

/** Space between the icon and the popover, and kept clear of the window edges. */
const GAP = 8;

/**
 * The app's explanatory hint: a small info icon that reveals a short note on
 * hover or keyboard focus. Use it instead of secondary body text so
 * explanations stay legible rather than shrinking to fit beside a control.
 *
 * The popover renders into the document body with fixed positioning, so a
 * scrolling container cannot clip it. It opens above the icon, or below
 * when there is no room above, and stays inside the window.
 */
export function InfoHint({ label, text, align = "left" }: Props) {
  const id = useId();
  const anchorRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLSpanElement>(null);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);
  const open = hovered || focused;

  const place = useCallback(() => {
    const anchor = anchorRef.current?.getBoundingClientRect();
    const popover = popoverRef.current?.getBoundingClientRect();
    if (!anchor || !popover) return;
    const above = anchor.top - GAP - popover.height;
    const top = above >= GAP ? above : anchor.bottom + GAP;
    const preferred = align === "right" ? anchor.right - popover.width : anchor.left;
    const left = Math.max(GAP, Math.min(preferred, window.innerWidth - popover.width - GAP));
    setPosition({ top, left });
  }, [align]);

  useLayoutEffect(() => {
    if (open) place();
  }, [open, place, text]);

  useEffect(() => {
    if (!open) return;
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    return () => {
      window.removeEventListener("scroll", place, true);
      window.removeEventListener("resize", place);
    };
  }, [open, place]);

  return (
    <span className="inline-flex" onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
      <button
        ref={anchorRef}
        type="button"
        aria-label={`More information about ${label}`}
        aria-describedby={id}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="cursor-help text-tertiary hover:text-secondary rounded transition-colors focus:outline-none focus:ring-2 focus:ring-accent"
      >
        <Info size={14} strokeWidth={1.8} />
      </button>
      {createPortal(
        <span
          ref={popoverRef}
          id={id}
          role="tooltip"
          style={{ top: position?.top ?? 0, left: position?.left ?? 0 }}
          className={`fixed z-[60] w-56 rounded-md border border-border-subtle bg-bg-card p-3
            text-xs font-normal normal-case tracking-normal text-primary shadow-lg whitespace-normal
            pointer-events-none transition-[opacity,visibility] duration-150
            ${open && position ? "opacity-100 visible" : "opacity-0 invisible"}`}
        >
          {text}
        </span>,
        document.body,
      )}
    </span>
  );
}
