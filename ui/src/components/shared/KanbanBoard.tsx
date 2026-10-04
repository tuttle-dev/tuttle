import { useState, useCallback, useRef, type ReactNode } from "react";
import { GripVertical } from "lucide-react";
import { tint, onTint } from "./status-colors";

export type BoardColumn = { id: string; label: string; color: string };

export function useStageStore(
  storageKey: string,
  columns: BoardColumn[],
  defaultColumn: (entity: { id: number; [k: string]: unknown }) => string,
) {
  const key = `tuttle.board.${storageKey}`;
  const [stages, setStages] = useState<Record<number, string>>(() => {
    try { return JSON.parse(localStorage.getItem(key) || "{}"); }
    catch { return {}; }
  });

  const columnFor = useCallback(
    (entity: { id: number; [k: string]: unknown }) => stages[entity.id] || defaultColumn(entity),
    [stages, defaultColumn],
  );
  const setColumn = useCallback((entityId: number, colId: string) => {
    setStages((prev) => { const next = { ...prev, [entityId]: colId }; localStorage.setItem(key, JSON.stringify(next)); return next; });
  }, [key]);
  const removeEntity = useCallback((entityId: number) => {
    setStages((prev) => { const next = { ...prev }; delete next[entityId]; localStorage.setItem(key, JSON.stringify(next)); return next; });
  }, [key]);

  return { columnFor, setColumn, removeEntity, columns };
}

type Props<T extends { id: number }> = {
  entities: T[]; columns: BoardColumn[];
  columnFor: (e: T) => string;
  onMove: (entityId: number, targetColumn: string) => void;
  renderCard: (entity: T, column: BoardColumn) => ReactNode;
};

export function KanbanBoard<T extends { id: number }>({ entities, columns, columnFor, onMove, renderCard }: Props<T>) {
  const [dragId, setDragId] = useState<number | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const dragRef = useRef<number | null>(null);

  const inCol = (colId: string) => entities.filter((e) => columnFor(e) === colId);

  return (
    <div className="flex flex-col h-full">
      {/* Summary header */}
      <div className="flex items-center gap-4 px-5 py-3 shrink-0 border-b border-border-subtle">
        {columns.map((col) => (
          <div key={col.id} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: col.color }} />
            <span className="text-sm font-medium text-secondary">{col.label}</span>
            <span className="text-xs font-bold px-1.5 py-px rounded-full"
              style={{ background: tint(col.color, 20), color: onTint(col.color) }}>
              {inCol(col.id).length}
            </span>
          </div>
        ))}
        <span className="ml-auto text-sm text-tertiary">{entities.length} total</span>
      </div>

      {/* Columns */}
      <div className="flex flex-1 overflow-hidden">
        {columns.map((col, i) => {
          const items = inCol(col.id);
          const isTarget = dropTarget === col.id;
          return (
            <div key={col.id}
              className={`flex-1 flex flex-col overflow-hidden transition-colors ${i < columns.length - 1 ? "border-r border-border-subtle" : ""}`}
              style={{ background: isTarget ? tint(col.color, 5) : undefined }}
              onDragOver={(e) => { e.preventDefault(); setDropTarget(col.id); }}
              onDragLeave={() => setDropTarget(null)}
              onDrop={(e) => { e.preventDefault(); setDropTarget(null); if (dragRef.current != null) onMove(dragRef.current, col.id); setDragId(null); dragRef.current = null; }}>
              <div className="px-2 pt-3 pb-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ background: col.color }} />
                  <span className="text-xs font-bold uppercase tracking-wider text-secondary">{col.label}</span>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-2">
                {items.map((ent) => (
                  <div key={ent.id} draggable
                    onDragStart={() => { setDragId(ent.id); dragRef.current = ent.id; }}
                    onDragEnd={() => { setDragId(null); dragRef.current = null; setDropTarget(null); }}
                    className="rounded-lg bg-bg-card cursor-grab active:cursor-grabbing transition-shadow"
                    style={{
                      border: `1px solid ${dragId === ent.id ? col.color : "var(--color-border-subtle)"}`,
                      opacity: dragId === ent.id ? 0.5 : 1,
                    }}>
                    <div className="relative py-3 pr-3 pl-4">
                      {/* Handle sits in the card's left padding so content gets the full column width. */}
                      <GripVertical size={12} className="absolute left-0.5 top-3.5 text-muted" />
                      <div>{renderCard(ent, col)}</div>
                    </div>
                  </div>
                ))}
                {items.length === 0 && (
                  <div className="flex items-center justify-center py-8 text-sm text-tertiary rounded-lg border border-dashed border-border-subtle">
                    Drop here
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
