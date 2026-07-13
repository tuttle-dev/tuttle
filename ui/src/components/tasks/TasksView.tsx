import { useEffect, useState } from "react";
import { CheckSquare, Circle, CheckCircle2, X } from "lucide-react";
import { rpc } from "../../api/rpc";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import type { Entity } from "../../api/types";

export function TasksView() {
  const [tasks, setTasks] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(true); }, []);

  async function load(showSpinner = false) {
    if (showSpinner) setLoading(true);
    const res = await rpc<Entity[]>("tasks.get_all");
    if (res.ok && Array.isArray(res.data)) setTasks(res.data);
    if (showSpinner) setLoading(false);
  }

  async function markDone(id: number) {
    await rpc("tasks.mark_done", { id });
    await load();
  }

  async function dismiss(id: number) {
    await rpc("tasks.dismiss", { id });
    await load();
  }

  async function reopen(id: number) {
    await rpc("tasks.reopen", { id });
    await load();
  }

  async function clearCompleted() {
    const done = tasks.filter((t) => t.status === "done" || t.status === "dismissed");
    for (const t of done) {
      await rpc("tasks.dismiss", { id: t.id });
    }
    await load();
  }

  if (loading) {
    return <div className="flex items-center justify-center h-full text-secondary">Loading tasks…</div>;
  }

  if (tasks.length === 0) {
    return <EmptyStateIntro icon={CheckSquare} description="You're all caught up — no pending tasks." />;
  }

  const pending = tasks.filter((t) => t.status === "pending");
  const completed = tasks.filter((t) => t.status === "done" || t.status === "dismissed");

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-lg font-semibold mb-5">Tasks</h1>

      {pending.length > 0 && (
        <div className="space-y-2 mb-6">
          {pending.map((task) => (
            <TaskCard
              key={task.id as number}
              task={task}
              onDone={() => markDone(task.id as number)}
              onDismiss={() => dismiss(task.id as number)}
            />
          ))}
        </div>
      )}

      {completed.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-medium uppercase tracking-wide text-tertiary">
              Completed
            </h2>
            <button
              onClick={clearCompleted}
              className="text-xs px-2 py-1 rounded border border-border-subtle text-tertiary hover:text-secondary hover:border-border transition-colors"
            >
              Clear all
            </button>
          </div>
          {completed.map((task) => {
            const isTutorial = ((task.key as string) ?? "").startsWith("tutorial:");
            return (
              <TaskCard
                key={task.id as number}
                task={task}
                done
                onReopen={!isTutorial ? () => reopen(task.id as number) : undefined}
                onDismiss={() => dismiss(task.id as number)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function TaskCard({ task, done, onDone, onDismiss, onReopen }: {
  task: Entity;
  done?: boolean;
  onDone?: () => void;
  onDismiss?: () => void;
  onReopen?: () => void;
}) {
  const [confirmDismiss, setConfirmDismiss] = useState(false);
  const key = (task.key as string) ?? "";
  const isTutorial = key.startsWith("tutorial:");

  return (
    <div className={`
      rounded-lg border px-4 py-3 transition-all group
      ${done
        ? "border-border-subtle bg-bg-sidebar opacity-60"
        : "border-border-subtle bg-bg-card hover:border-border"}
    `}>
      <div className="flex items-start gap-3">
        <button
          onClick={done ? onReopen : onDone}
          disabled={done && !onReopen}
          className={`mt-0.5 shrink-0 transition-colors ${
            done && onReopen
              ? "text-green-500 hover:text-secondary cursor-default"
              : done
              ? "text-green-500 cursor-default"
              : "text-secondary hover:text-green-500 cursor-default"
          }`}
          title={done ? (onReopen ? "Reopen" : "Completed") : "Mark done"}
        >
          {done ? <CheckCircle2 size={18} /> : <Circle size={18} />}
        </button>

        <div className="flex-1 min-w-0">
          <div className={`text-sm font-medium ${done ? "line-through text-tertiary" : ""}`}>
            {String(task.title ?? "")}
          </div>
          {!done && task.description ? (
            <div className="text-xs text-tertiary mt-1 leading-relaxed">
              {String(task.description)}
            </div>
          ) : null}
          {!done && isTutorial && (
            <span className="inline-block mt-1.5 text-[10px] uppercase tracking-wide text-tertiary bg-bg-hover px-1.5 py-0.5 rounded">
              Getting started
            </span>
          )}
        </div>

        {onDismiss && !confirmDismiss && (
          <button
            onClick={() => setConfirmDismiss(true)}
            className="shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 text-muted hover:text-secondary transition-all"
          >
            <X size={14} />
          </button>
        )}
        {onDismiss && confirmDismiss && (
          <div className="shrink-0 flex items-center gap-1.5">
            <button
              onClick={onDismiss}
              className="text-[11px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
            >
              Remove
            </button>
            <button
              onClick={() => setConfirmDismiss(false)}
              className="text-[11px] px-1.5 py-0.5 rounded text-muted hover:text-secondary transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
