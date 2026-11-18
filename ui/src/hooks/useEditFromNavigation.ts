import { useEffect, useRef } from "react";
import type { NavigationFilter } from "../components/shared/NavigationContext";

/**
 * Opens a list/detail view's edit form when navigation asks for it
 * (`{ <kind>Id, edit: true }`, as the tour does), once per navigation:
 * cancelling the form keeps it closed.
 */
export function useEditFromNavigation(
  filter: NavigationFilter,
  wantedId: number | undefined,
  selectedId: number | undefined,
  openEdit: () => void,
) {
  const handled = useRef<NavigationFilter | null>(null);
  useEffect(() => {
    if (!filter.edit || wantedId == null || selectedId !== wantedId || handled.current === filter) return;
    handled.current = filter;
    openEdit();
  }, [filter, wantedId, selectedId, openEdit]);
}
