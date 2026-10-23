import { useEffect, useState } from "react";
import { ArrowRight, CheckSquare, Circle, CheckCircle2, Repeat, X, Zap, CalendarDays } from "lucide-react";
import { rpc } from "../../api/rpc";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { LoadError, LoadingState } from "../shared/LoadStates";
import { PageLayout, ToolbarFilterGroup } from "../shared/ToolbarButtons";
import { useNavigation, type NavigationFilter } from "../shared/NavigationContext";
import { localDateIso } from "../../api/entity";
import type { Entity } from "../../api/types";
import { RuleComposer } from "./RuleComposer";
import { RulesList } from "./RulesList";
import { fmtDay, relDay, ruleSentence, subjectDestination, type RuleOptions, type TaskRule } from "./rules";

type Destination = { view: string; filter?: NavigationFilter };
type Mode = "tasks" | "rules";

/** Tells the sidebar how many tasks are pending. */
export const TASKS_CHANGED_EVENT = "tuttle:tasks-changed";

// Where each getting-started task gets done, by task key (see tuttle/app/tasks/generator.py).
const DESTINATIONS: Record<string, Destination> = {
  "tutorial:first_contact": { view: "contacts" },
  "tutorial:first_client": { view: "clients" },
  "tutorial:first_contract": { view: "contracts" },
  "tutorial:first_project": { view: "projects" },
  "tutorial:first_invoice": { view: "invoicing" },
  "tutorial:configure_ai": { view: "settings", filter: { tab: "llm" } },
  "tutorial:import_document": { view: "import" },
};

function destinationOf(task: Entity): Destination | undefined {
  return DESTINATIONS[(task.key as string) ?? ""]
    ?? subjectDestination((task.subject_type as string) ?? null, (task.subject_id as number) ?? null);
}

export function TasksView() {
  const { navigate } = useNavigation();
  const [mode, setMode] = useState<Mode>("tasks");
  const [tasks, setTasks] = useState<Entity[]>([]);
  const [rules, setRules] = useState<TaskRule[]>([]);
  const [options, setOptions] = useState<RuleOptions | null>(null);
  const [composing, setComposing] = useState<TaskRule | "new" | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => { load(true); }, []);

  async function load(showSpinner = false) {
    if (showSpinner) setLoading(true);
    setLoadFailed(false);
    const [tasksRes, rulesRes, optionsRes] = await Promise.all([
      rpc<Entity[]>("tasks.get_all"),
      rpc<TaskRule[]>("tasks.get_rules"),
      rpc<RuleOptions>("tasks.rule_options"),
    ]);
    setLoadFailed(!tasksRes.ok || !rulesRes.ok || !optionsRes.ok);
    if (tasksRes.ok && Array.isArray(tasksRes.data)) {
      setTasks(tasksRes.data);
      const pending = tasksRes.data.filter((t) => t.status === "pending").length;
      window.dispatchEvent(new CustomEvent(TASKS_CHANGED_EVENT, { detail: pending }));
    }
    if (rulesRes.ok && Array.isArray(rulesRes.data)) setRules(rulesRes.data);
    if (optionsRes.ok && optionsRes.data) setOptions(optionsRes.data);
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

  async function togglePause(rule: TaskRule) {
    await rpc("tasks.set_rule_paused", { id: rule.id, paused: !rule.paused });
    await load();
  }

  const pending = tasks
    .filter((t) => t.status === "pending")
    // Getting started first, then by the date each task is about.
    .sort((a, b) => String(a.due_date ?? "").localeCompare(String(b.due_date ?? "")));
  const completed = tasks.filter((t) => t.status === "done" || t.status === "dismissed");
  const ruleById = new Map(rules.map((r) => [r.id, r]));

  const toggle = (
    <ToolbarFilterGroup
      options={["tasks", "rules"] as const}
      value={mode}
      onChange={setMode}
      icons={{ tasks: <CheckSquare size={12} />, rules: <Zap size={12} /> }}
      labels={{
        tasks: <>Tasks <span className="text-muted tabular-nums">{pending.length}</span></>,
        rules: <>Rules <span className="text-muted tabular-nums">{rules.length}</span></>,
      }}
    />
  );

  const composer = composing && options && (
    <RuleComposer
      rule={composing === "new" ? null : composing}
      options={options}
      onClose={() => setComposing(null)}
      onSaved={() => { setComposing(null); load(); }}
      onDeleted={() => { setComposing(null); load(); }}
    />
  );

  if (loadFailed) return <PageLayout title="Tasks" fallback={<LoadError what="tasks" onRetry={() => load(true)} />} />;
  if (loading) return <PageLayout title="Tasks" fallback={<LoadingState />} />;

  if (mode === "rules") {
    return (
      <PageLayout title="Tasks" right={toggle}>
        <RulesList rules={rules} options={options} onEdit={setComposing} onNew={() => setComposing("new")} onTogglePause={togglePause} />
        {composer}
      </PageLayout>
    );
  }

  if (tasks.length === 0) {
    return (
      <PageLayout title="Tasks" right={toggle}
        fallback={<EmptyStateIntro icon={CheckSquare} description="You're all caught up — no pending tasks." />} />
    );
  }

  return (
    <PageLayout title="Tasks" right={toggle}>
      {pending.length > 0 && (
        <div className="space-y-2 mb-6">
          {pending.map((task) => {
            const dest = destinationOf(task);
            const rule = ruleById.get(task.rule_id as number);
            return (
              <TaskCard
                key={task.id as number}
                task={task}
                rule={rule}
                ruleLabel={rule ? ruleSentence(rule, options) : undefined}
                onOpen={dest ? () => navigate(dest.view, dest.filter) : undefined}
                onDone={() => markDone(task.id as number)}
                onDismiss={() => dismiss(task.id as number)}
                onEditRule={rule ? () => setComposing(rule) : undefined}
              />
            );
          })}
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
      {composer}
    </PageLayout>
  );
}

function TaskCard({ task, rule, ruleLabel, done, onOpen, onDone, onDismiss, onReopen, onEditRule }: {
  task: Entity;
  rule?: TaskRule;
  ruleLabel?: string;
  done?: boolean;
  onOpen?: () => void;
  onDone?: () => void;
  onDismiss?: () => void;
  onReopen?: () => void;
  onEditRule?: () => void;
}) {
  const [confirmDismiss, setConfirmDismiss] = useState(false);
  const key = (task.key as string) ?? "";
  const isTutorial = key.startsWith("tutorial:");
  const dueDate = (task.due_date as string) || null;
  const today = localDateIso();
  const RuleIcon = rule?.kind === "event" ? Zap : rule?.unit ? Repeat : CalendarDays;
  // The card navigates; its own buttons must not.
  const own = (fn?: () => void) => (e: React.MouseEvent) => { e.stopPropagation(); fn?.(); };

  return (
    <div
      role={onOpen ? "button" : undefined}
      tabIndex={onOpen ? 0 : undefined}
      onClick={onOpen}
      onKeyDown={onOpen ? (e) => {
        if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onOpen(); }
      } : undefined}
      className={`
      rounded-lg border px-4 py-3 transition-all group
      ${done
        ? "border-border-subtle bg-bg-sidebar opacity-60"
        : onOpen
        ? "border-border-subtle bg-bg-card hover:border-accent hover:bg-bg-hover cursor-pointer"
        : "border-border-subtle bg-bg-card hover:border-border"}
    `}>
      <div className="flex items-start gap-3">
        <button
          onClick={own(done ? onReopen : onDone)}
          disabled={done && !onReopen}
          className={`mt-0.5 shrink-0 transition-colors ${
            done && onReopen
              ? "text-status-success hover:text-secondary cursor-default"
              : done
              ? "text-status-success cursor-default"
              : "text-secondary hover:text-status-success cursor-default"
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
            <div className="text-xs text-tertiary mt-1 leading-relaxed max-w-xl">
              {String(task.description)}
            </div>
          ) : null}
          {!done && isTutorial && (
            <span className="inline-block mt-1.5 text-[10px] uppercase tracking-wide text-tertiary bg-bg-hover px-1.5 py-0.5 rounded">
              Getting started
            </span>
          )}
          {!done && (dueDate || ruleLabel) && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs">
              {dueDate && (
                <span className={`tabular-nums ${dueDate > today ? "text-accent" : "text-tertiary"}`}>
                  {fmtDay(dueDate)} · {relDay(dueDate)}
                </span>
              )}
              {ruleLabel && (
                <button type="button" onClick={own(onEditRule)} title="Edit the rule"
                  className="inline-flex items-center gap-1 text-muted hover:text-accent hover:underline">
                  <RuleIcon size={11} /> {ruleLabel}
                </button>
              )}
            </div>
          )}
        </div>

        {onDismiss && !confirmDismiss && (
          <button
            onClick={own(() => setConfirmDismiss(true))}
            className="shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 text-muted hover:text-secondary transition-all"
          >
            <X size={14} />
          </button>
        )}
        {onDismiss && confirmDismiss && (
          <div className="shrink-0 flex items-center gap-1.5">
            <button
              onClick={own(onDismiss)}
              className="text-[11px] px-1.5 py-0.5 rounded bg-status-danger/10 text-status-danger hover:bg-status-danger/20 transition-colors"
            >
              Remove
            </button>
            <button
              onClick={own(() => setConfirmDismiss(false))}
              className="text-[11px] px-1.5 py-0.5 rounded text-muted hover:text-secondary transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
        {onOpen && <ArrowRight size={14} className="shrink-0 mt-0.5 text-tertiary group-hover:text-primary" />}
      </div>
    </div>
  );
}
