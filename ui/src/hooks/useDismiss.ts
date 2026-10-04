import { useEffect, useRef, type MouseEvent } from "react";

/**
 * Closes a dialog on Escape or on a click on its backdrop. Spread the
 * returned props onto the backdrop element.
 */
export function useDismiss(onClose: () => void, enabled = true) {
  useEffect(() => {
    if (!enabled) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, enabled]);

  // A drag that starts inside the panel (e.g. selecting text) and ends on
  // the backdrop must not close it.
  const pressedBackdrop = useRef(false);
  return {
    onMouseDown: (e: MouseEvent) => { pressedBackdrop.current = e.target === e.currentTarget; },
    onClick: (e: MouseEvent) => {
      if (enabled && pressedBackdrop.current && e.target === e.currentTarget) onClose();
    },
  };
}
