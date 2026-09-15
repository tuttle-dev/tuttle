import { useEffect, useState } from "react";
import { Target, Plus, Pencil, Trash2, Save, X, Trophy } from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num, bool, formatDate } from "../../api/entity";
import type { Entity } from "../../api/types";

interface GoalEntry {
  goal: Entity;
  progress: number;
  ytd_revenue: number;
  currency: string;
}

interface GoalFormData {
  id?: number;
  title: string;
  target_amount: number;
  target_date: string;
}

function fmt(value: number, currency = "EUR"): string {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${value.toFixed(0)}`;
  }
}

export function FinancialGoalsCard() {
  const [entries, setEntries] = useState<GoalEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Entity | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { load(); }, []);

  async function load() {
    const res = await rpc<GoalEntry[]>("dashboard.get_financial_goals");
    if (res.ok && Array.isArray(res.data)) setEntries(res.data);
    setLoading(false);
  }

  function startCreate() {
    setEditing(null);
    setShowForm(true);
    setError(null);
  }

  function startEdit(goal: Entity) {
    setEditing(goal);
    setShowForm(true);
    setError(null);
  }

  function closeForm() {
    setShowForm(false);
    setEditing(null);
    setError(null);
  }

  async function handleSave(data: GoalFormData) {
    setError(null);
    const res = await rpc("dashboard.save_financial_goal", { ...data });
    if (res.ok) {
      closeForm();
      await load();
    } else {
      setError(res.error || "Failed to save goal.");
    }
  }

  async function handleDelete(id: number) {
    setError(null);
    const res = await rpc("dashboard.delete_financial_goal", { goal_id: id });
    if (res.ok) {
      await load();
    } else {
      setError(res.error || "Failed to delete goal.");
    }
  }

  if (loading) return null;

  return (
    <div className="rounded-lg bg-bg-card border border-border-subtle p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-secondary">Financial Goals</h2>
        {!showForm && (
          <button
            onClick={startCreate}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-xs text-secondary hover:text-primary hover:bg-bg-hover transition-colors"
          >
            <Plus size={12} /> Add Goal
          </button>
        )}
      </div>

      {error && (
        <div className="p-2 rounded-md bg-red-500/10 border border-red-500/30 text-xs text-red-400">{error}</div>
      )}

      {entries.length === 0 && !showForm ? (
        <div className="flex flex-col items-center justify-center py-6 gap-2 text-tertiary">
          <Target size={28} strokeWidth={1.2} />
          <span className="text-xs text-center max-w-xs">
            Set a revenue target to track your progress against it through the year.
          </span>
        </div>
      ) : (
        entries.map((entry) => (
          <GoalRow
            key={entry.goal.id as number}
            entry={entry}
            onEdit={() => startEdit(entry.goal)}
            onDelete={() => handleDelete(entry.goal.id as number)}
          />
        ))
      )}

      {showForm && (
        <GoalForm goal={editing} onSave={handleSave} onCancel={closeForm} />
      )}
    </div>
  );
}

/* ---------- Goal row ---------- */

function GoalRow({ entry, onEdit, onDelete }: {
  entry: GoalEntry; onEdit: () => void; onDelete: () => void;
}) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const { goal, progress, ytd_revenue, currency } = entry;

  useEffect(() => { setConfirmDelete(false); }, [goal.id]);

  const title = str(goal, "title");
  const target = num(goal, "target_amount");
  const reached = bool(goal, "is_reached");

  return (
    <div className="space-y-1 group">
      <div className="flex items-baseline justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {reached && <Trophy size={12} className="text-emerald-400 shrink-0" />}
          <span className="text-xs font-medium truncate">{title}</span>
          <span className="text-[11px] text-tertiary shrink-0">
            by {formatDate(str(goal, "target_date"))}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-secondary tabular-nums">
            {fmt(ytd_revenue, currency)} / {fmt(target, currency)}
          </span>
          {!confirmDelete ? (
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={onEdit} title="Edit goal"
                className="p-1 rounded text-tertiary hover:text-primary hover:bg-bg-hover transition-colors">
                <Pencil size={11} />
              </button>
              <button onClick={() => setConfirmDelete(true)} title="Delete goal"
                className="p-1 rounded text-tertiary hover:text-red-400 hover:bg-red-500/10 transition-colors">
                <Trash2 size={11} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-red-400">Delete?</span>
              <button onClick={() => { setConfirmDelete(false); onDelete(); }}
                className="px-1.5 py-0.5 rounded text-[11px] font-medium bg-red-500 text-white hover:bg-red-600 transition-colors">
                Delete
              </button>
              <button onClick={() => setConfirmDelete(false)}
                className="px-1.5 py-0.5 rounded text-[11px] font-medium text-secondary hover:text-primary border border-border-subtle transition-colors">
                Keep
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="h-1.5 w-full rounded-full bg-bg-hover overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${reached ? "bg-emerald-400" : "bg-secondary"}`}
          style={{ width: `${Math.max(0, Math.min(progress, 1)) * 100}%` }}
        />
      </div>
    </div>
  );
}

/* ---------- Form ---------- */

function GoalForm({ goal, onSave, onCancel }: {
  goal: Entity | null;
  onSave: (data: GoalFormData) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState(goal ? str(goal, "title") : "");
  const [amountStr, setAmountStr] = useState(goal ? str(goal, "target_amount") : "");
  const [targetDate, setTargetDate] = useState(
    goal ? str(goal, "target_date") : `${new Date().getFullYear()}-12-31`
  );
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    await onSave({
      ...(goal ? { id: goal.id as number } : {}),
      title,
      target_amount: parseFloat(amountStr) || 0,
      target_date: targetDate,
    });
    setSaving(false);
  }

  const canSave = title.trim() !== "" && amountStr.trim() !== "" && targetDate !== "";

  return (
    <form onSubmit={handleSubmit} className="pt-3 border-t border-border-subtle space-y-2">
      <div className="flex items-end gap-2">
        <div className="flex-1 min-w-0">
          <label className="block text-[11px] text-tertiary mb-1">Title</label>
          <input
            type="text" value={title} onChange={(e) => setTitle(e.target.value)}
            autoFocus required placeholder="e.g. Yearly revenue"
            className="w-full px-2 py-1.5 rounded-md text-xs bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted"
          />
        </div>
        <div className="w-28 shrink-0">
          <label className="block text-[11px] text-tertiary mb-1">Target</label>
          <input
            type="number" step="0.01" min="0" value={amountStr}
            onChange={(e) => setAmountStr(e.target.value)} required placeholder="60000"
            className="w-full px-2 py-1.5 rounded-md text-xs bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted"
          />
        </div>
        <div className="w-36 shrink-0">
          <label className="block text-[11px] text-tertiary mb-1">By</label>
          <input
            type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} required
            className="w-full px-2 py-1.5 rounded-md text-xs bg-bg-sidebar text-primary border border-border-subtle outline-none focus:border-accent transition-colors"
          />
        </div>
        <div className="flex items-center gap-1 shrink-0 pb-0.5">
          <button type="submit" disabled={saving || !canSave} title="Save"
            className="flex items-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium text-primary hover:bg-bg-hover transition-colors disabled:opacity-40">
            <Save size={12} /> {saving ? "Saving…" : "Save"}
          </button>
          <button type="button" onClick={onCancel} title="Cancel"
            className="p-1.5 rounded-md text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
            <X size={12} />
          </button>
        </div>
      </div>
    </form>
  );
}
