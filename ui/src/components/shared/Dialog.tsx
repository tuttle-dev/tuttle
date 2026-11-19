import type { ReactNode } from "react";
import { useDismiss } from "../../hooks/useDismiss";

/**
 * A modal dialog that never outgrows the window: a dimmed backdrop and a panel
 * at most 85% of the window high. Put its parts in it: `DialogHeader`, then
 * `DialogBody`, which scrolls, then `DialogFooter`. Escape or a click on the
 * backdrop closes it.
 */
export function Dialog({
  onClose, dismissible = true, width, surface = "bg-bg-content border border-border-subtle", backdropClassName, labelledBy, children,
}: {
  onClose: () => void;
  /** False while the dialog must stay open, e.g. during a request. */
  dismissible?: boolean;
  /** Width of the panel, e.g. "w-[560px]". */
  width: string;
  /** Background and border of the panel. */
  surface?: string;
  backdropClassName?: string;
  /** Id of the heading; marks the panel as a modal dialog for assistive technology. */
  labelledBy?: string;
  children: ReactNode;
}) {
  const backdrop = useDismiss(onClose, dismissible);
  return (
    <div className={withClasses("fixed inset-0 z-50 flex items-center justify-center bg-black/50", backdropClassName)} {...backdrop}>
      <div {...(labelledBy ? { role: "dialog", "aria-modal": true, "aria-labelledby": labelledBy } : {})}
        className={`${surface} rounded-xl shadow-2xl ${width} max-h-[85vh] flex flex-col overflow-hidden`}>
        {children}
      </div>
    </div>
  );
}

/** The top of a `Dialog`, which keeps its place. `className` lays out its content. */
export function DialogHeader({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={withClasses("px-5 py-4 border-b border-border-subtle shrink-0", className)}>{children}</div>;
}

/** The content of a `Dialog`, which scrolls. `className` sets its padding and spacing. */
export function DialogBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={withClasses("flex-1 overflow-y-auto", className)}>{children}</div>;
}

/** The bottom of a `Dialog`, which keeps its place. `className` lays out its content. */
export function DialogFooter({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={withClasses("px-5 py-3 border-t border-border-subtle shrink-0", className)}>{children}</div>;
}

function withClasses(base: string, extra?: string): string {
  return extra ? `${base} ${extra}` : base;
}
