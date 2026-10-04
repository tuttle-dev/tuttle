import { useLayoutEffect, useRef } from "react";
import type { Entity } from "../api/types";

/**
 * Keeps a list/detail view's selection on a visible row, so the detail pane
 * is only empty when the list is.
 *
 * - Nothing selected, or the selection filtered out → first visible item
 *   (the first `preferred` one, if any).
 * - Selected item deleted → the item that took its place.
 * - Back from a form that cleared the selection → the previous item.
 *
 * Pass `enabled: false` while a create/edit form owns the detail pane.
 */
export function useAutoSelect(
  all: Entity[],
  visible: Entity[],
  selected: Entity | null,
  setSelected: (e: Entity | null) => void,
  { enabled = true, preferred }: { enabled?: boolean; preferred?: (e: Entity) => boolean } = {},
) {
  const last = useRef<{ id: number; index: number } | null>(null);

  useLayoutEffect(() => {
    if (!enabled) return;
    const index = selected ? visible.findIndex((e) => e.id === selected.id) : -1;
    if (selected && index >= 0) {
      last.current = { id: selected.id, index };
      return;
    }
    if (visible.length === 0) {
      if (selected) setSelected(null);
      return;
    }
    const prev = last.current;
    let next: Entity | undefined;
    if (prev && !all.some((e) => e.id === prev.id)) next = visible[Math.min(prev.index, visible.length - 1)];
    else if (prev && !selected) next = visible.find((e) => e.id === prev.id);
    setSelected(next ?? (preferred && visible.find(preferred)) ?? visible[0]);
  });
}
