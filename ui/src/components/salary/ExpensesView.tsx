import { useEffect, useState, useRef } from "react";
import { Receipt, Plus, Trash2, Save, X, Info } from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num } from "../../api/entity";
import { Toolbar, ToolbarButtonPrimary, ListDetailLayout, LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { useFieldRequirements } from "../../hooks/useFieldRequirements";
import type { Entity } from "../../api/types";

type Mode = "view" | "edit" | "create";

const CYCLE_OPTIONS = [
  { value: "hourly", label: "Hourly" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "yearly", label: "Yearly" },
];

const CATEGORY_OPTIONS = [
  { value: "operating", label: "Operating" },
  { value: "insurance", label: "Insurance" },
  { value: "professional", label: "Professional" },
  { value: "other", label: "Other" },
];

/** Normalize a recurring amount to its monthly equivalent (mirrors backend `_normalize_to_monthly`). */
const PERIOD_TO_MONTHLY_DIVISOR: Record<string, number> = {
  monthly: 1,
  quarterly: 3,
  yearly: 12,
  weekly: 0.25,
  daily: 30,
  hourly: 160,
};

function toMonthly(amount: number, period: string): number {
  const divisor = PERIOD_TO_MONTHLY_DIVISOR[period] ?? 1;
  return amount / divisor;
}

function fmt(value: number, currency = "EUR"): string {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
  } catch { return `${currency} ${value.toFixed(2)}`; }
}

export function ExpensesView() {
  const [expenses, setExpenses] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<Mode>("view");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const selectedIdRef = useRef<number | null>(null);

  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);
  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    const res = await rpc<Entity[]>("salary.get_expenses");
    if (res.ok && res.data) {
      setExpenses(res.data);
      const currentId = selectedIdRef.current;
      if (currentId != null) {
        const updated = res.data.find((e) => e.id === currentId);
        setSelected(updated || null);
      }
    }
    setLoading(false);
  }

  function startCreate() {
    setSelected(null);
    setMode("create");
    setDeleteError(null);
    setSaveError(null);
  }

  function selectExpense(e: Entity) {
    setSelected(e);
    setMode("view");
    setDeleteError(null);
    setSaveError(null);
  }

  async function handleSave(data: ExpenseFormData) {
    setSaveError(null);
    const expense: Record<string, unknown> = {
      title: data.title,
      amount: data.amount,
      currency: data.currency,
      period: data.period,
      category: data.category,
    };
    if (mode === "edit" && selected) {
      expense.id = selected.id;
    }
    const res = await rpc("salary.save_expense", expense);
    if (res.ok) {
      setSaveError(null);
      setMode("view");
      await load();
    } else {
      setSaveError(res.error || "Failed to save recurring expense.");
    }
  }

  async function handleDelete(id: number) {
    setDeleteError(null);
    const res = await rpc("salary.delete_expense", { expense_id: id });
    if (res.ok) {
      setSelected(null);
      setMode("view");
      await load();
    } else {
      setDeleteError(res.error || "Failed to delete recurring expense.");
    }
  }

  const sorted = [...expenses].sort((a, b) => {
    const aTitle = str(a, "title") || "";
    const bTitle = str(b, "title") || "";
    return aTitle.localeCompare(bTitle);
  });

  const filtered = sorted.filter((e) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const title = str(e, "title").toLowerCase();
    const category = str(e, "category").toLowerCase();
    return title.includes(q) || category.includes(q);
  });

  // Group filtered expenses by category
  const grouped = new Map<string, Entity[]>();
  for (const e of filtered) {
    const cat = str(e, "category") || "other";
    const label = cat.charAt(0).toUpperCase() + cat.slice(1);
    if (!grouped.has(label)) grouped.set(label, []);
    grouped.get(label)!.push(e);
  }

  // Monthly total (all expenses, not just filtered)
  const monthlyTotal = expenses.reduce((sum, e) => {
    return sum + toMonthly(num(e, "amount"), str(e, "period"));
  }, 0);
  const totalCurrency = expenses.length > 0 ? str(expenses[0], "currency") : "EUR";

  if (loading && expenses.length === 0) {
    return <div className="flex items-center justify-center h-full text-secondary">Loading recurring expenses…</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <Toolbar
        title="Recurring Expenses"
        actions={<ToolbarButtonPrimary icon={<Plus size={13} />} label="New" onClick={startCreate} />}
        search={{ value: search, onChange: setSearch }}
      />

      {expenses.length === 0 && mode === "view" ? (
        <EmptyStateIntro
          icon={Receipt}
          description="Track your recurring business and personal expenses (e.g. health insurance, software) to accurately calculate your effective freelancer take-home salary."
        />
      ) : (
        <ListDetailLayout
          footer={
            <>
              {filtered.length} recurring expense{filtered.length !== 1 ? "s" : ""}
              {expenses.length > 0 && (
                <span className="ml-2 text-tertiary">
                  · {fmt(monthlyTotal, totalCurrency)}/mo
                </span>
              )}
            </>
          }
          list={
            filtered.length === 0 ? (
              <div className="p-4 text-sm text-center text-tertiary">No matches.</div>
            ) : (
              Array.from(grouped.entries()).map(([category, items]) => (
                <div key={category}>
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-tertiary bg-bg-sidebar sticky top-0 z-[1]">
                    {category}
                  </div>
                  {items.map((e) => (
                    <ExpenseRow
                      key={e.id}
                      expense={e}
                      isSelected={selected?.id === e.id && mode !== "create"}
                      onSelect={() => selectExpense(e)}
                    />
                  ))}
                </div>
              ))
            )
          }
          detail={
            mode === "create" ? (
              <ExpenseForm onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
            ) : mode === "edit" && selected ? (
              <ExpenseForm expense={selected} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
            ) : selected ? (
              <ExpenseDetail
                expense={selected}
                onEdit={() => setMode("edit")}
                onDelete={() => handleDelete(selected.id)}
                deleteError={deleteError}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-tertiary">
                <Receipt size={36} strokeWidth={1.2} />
                <span className="text-sm">Select an expense</span>
              </div>
            )
          }
        />
      )}
    </div>
  );
}

/* ---------- List row ---------- */

function ExpenseRow({ expense, isSelected, onSelect }: {
  expense: Entity; isSelected: boolean; onSelect: () => void;
}) {
  const title = str(expense, "title");
  const amount = num(expense, "amount");
  const currency = str(expense, "currency");
  const period = str(expense, "period");

  return (
    <button onClick={onSelect}
      className={`w-full text-left ${LIST_ROW_PADDING} border-b border-border-subtle transition-colors flex items-center gap-3
        ${isSelected ? "bg-bg-selected" : "hover:bg-bg-hover"}`}>
      <div className="w-9 h-9 rounded-full bg-bg-card flex items-center justify-center text-sm font-semibold text-secondary shrink-0">
        <Receipt size={16} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium truncate">{title}</div>
        <div className="text-xs text-tertiary truncate">
          {fmt(amount, currency)} / {period}
        </div>
      </div>
    </button>
  );
}

/* ---------- Detail view ---------- */

function ExpenseDetail({ expense, onEdit, onDelete, deleteError }: {
  expense: Entity; onEdit: () => void; onDelete: () => void; deleteError: string | null;
}) {
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  // Reset confirmation when the selected expense changes
  useEffect(() => { setDeleteConfirm(false); }, [expense.id]);

  const title = str(expense, "title");
  const amount = num(expense, "amount");
  const currency = str(expense, "currency");
  const period = str(expense, "period");
  const category = str(expense, "category");
  const monthly = toMonthly(amount, period);

  return (
    <div className="p-6 space-y-6 max-w-xl">
      <div className="flex items-center justify-between border-b border-border-subtle pb-4">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          <span className="inline-block text-xs font-medium px-2 py-0.5 rounded bg-accent/15 text-accent capitalize mt-1">
            {category}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onEdit}
            className="px-3 py-1.5 rounded-md text-sm border border-border-subtle hover:bg-bg-hover transition-colors">
            Edit
          </button>
          {!deleteConfirm ? (
            <button onClick={() => setDeleteConfirm(true)}
              className="p-2 rounded-md border border-border-subtle hover:border-red-500/30 hover:bg-red-500/10 text-secondary hover:text-red-400 transition-all"
              title="Delete expense">
              <Trash2 size={14} />
            </button>
          ) : (
            <div className="flex items-center gap-1.5 ml-1">
              <span className="text-xs text-red-400">Delete permanently?</span>
              <button onClick={() => { setDeleteConfirm(false); onDelete(); }}
                className="px-2 py-1 rounded-md text-xs font-medium bg-red-500 text-white hover:bg-red-600 transition-colors">
                Delete
              </button>
              <button onClick={() => setDeleteConfirm(false)}
                className="px-2 py-1 rounded-md text-xs font-medium text-secondary hover:text-primary border border-border-subtle transition-colors">
                Keep
              </button>
            </div>
          )}
        </div>
      </div>

      {deleteError && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">{deleteError}</div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <InfoRow icon={<Receipt size={14} />} label="Amount" value={fmt(amount, currency)} />
        <InfoRow icon={<Info size={14} />} label="Period" value={period.charAt(0).toUpperCase() + period.slice(1)} />
      </div>

      <div className="p-3 rounded-lg bg-bg-card border border-border-subtle">
        <div className="text-xs font-semibold uppercase tracking-wider text-tertiary">Monthly Equivalent</div>
        <div className="text-sm font-medium mt-0.5">{fmt(monthly, currency)}/mo</div>
      </div>
    </div>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-card border border-border-subtle">
      <span className="text-tertiary">{icon}</span>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-tertiary">{label}</div>
        <div className="text-sm">{value}</div>
      </div>
    </div>
  );
}

/* ---------- Form ---------- */

interface ExpenseFormData {
  title: string;
  amount: number;
  currency: string;
  period: string;
  category: string;
}

function ExpenseForm({ expense, onSave, onCancel, error }: {
  expense?: Entity;
  onSave: (data: ExpenseFormData) => void;
  onCancel: () => void;
  error?: string | null;
}) {
  const { isRequired } = useFieldRequirements("salary");
  const [title, setTitle] = useState(expense ? str(expense, "title") : "");
  const [amountStr, setAmountStr] = useState(expense ? str(expense, "amount") : "");
  const [currency, setCurrency] = useState(expense ? str(expense, "currency") : "EUR");
  const [period, setPeriod] = useState(expense ? str(expense, "period") : "monthly");
  const [category, setCategory] = useState(expense ? str(expense, "category") : "operating");
  const [saving, setSaving] = useState(false);
  const isNew = !expense;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    const amountVal = parseFloat(amountStr) || 0;
    await onSave({ title, amount: amountVal, currency, period, category });
    setSaving(false);
  }

  return (
    <form onSubmit={handleSubmit} className="p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{isNew ? "New Recurring Expense" : "Edit Recurring Expense"}</h2>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onCancel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors">
            <X size={14} /> Cancel
          </button>
          <button type="submit" disabled={saving || !title.trim() || !amountStr.trim()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-primary hover:bg-bg-hover transition-colors disabled:opacity-40">
            <Save size={14} /> {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

      <div className="space-y-4">
        <div>
          <label className="block text-xs text-tertiary mb-1">
            Title{isRequired("title") && <span className="text-accent ml-0.5">*</span>}
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
            required
            placeholder="e.g. Health Insurance"
            className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-tertiary mb-1">
              Amount{isRequired("amount") && <span className="text-accent ml-0.5">*</span>}
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={amountStr}
              onChange={(e) => setAmountStr(e.target.value)}
              required
              placeholder="e.g. 350.00"
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted"
            />
          </div>

          <div>
            <label className="block text-xs text-tertiary mb-1">
              Currency{isRequired("currency") && <span className="text-accent ml-0.5">*</span>}
            </label>
            <input
              type="text"
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              required
              placeholder="EUR"
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-tertiary mb-1">
              Recurrence Period{isRequired("period") && <span className="text-accent ml-0.5">*</span>}
            </label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors"
            >
              {CYCLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-tertiary mb-1">
              Category{isRequired("category") && <span className="text-accent ml-0.5">*</span>}
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors"
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}
    </form>
  );
}
