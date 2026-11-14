import { useEffect, useState, useRef } from "react";
import { Wallet, Plus } from "lucide-react";
import { rpc } from "../../api/rpc";
import { str, num } from "../../api/entity";
import { Toolbar, ToolbarButtonPrimary, ListDetailLayout, LIST_ROW_PADDING } from "../shared/ToolbarButtons";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import { DetailHeader, DetailAction, DetailDeleteAction, DetailSubmit, DETAIL_PANE } from "../shared/DetailHeader";
import { DetailFields, DetailField } from "../shared/DetailFields";
import { LoadError, LoadingState } from "../shared/LoadStates";
import { useAutoSelect } from "../../hooks/useAutoSelect";
import type { Entity } from "../../api/types";

type Mode = "view" | "edit" | "create";

const PERIOD_OPTIONS = [
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "yearly", label: "Yearly" },
];

/** Mirrors backend `OTHER_INCOME_KINDS`. */
const KIND_OPTIONS = [
  { value: "employment", label: "Employment" },
  { value: "pension", label: "Pension" },
  { value: "rental", label: "Rental" },
  { value: "capital", label: "Capital" },
  { value: "other", label: "Other" },
];

/** How many months one period spans (mirrors backend `PERIOD_TO_MONTHS`). */
const PERIOD_TO_MONTHS: Record<string, number> = {
  monthly: 1,
  quarterly: 3,
  yearly: 12,
  weekly: 12 / 52,
  daily: 12 / 365,
  hourly: 1 / 160,
};

function toYearly(amount: number, period: string): number {
  return (amount / (PERIOD_TO_MONTHS[period] ?? 1)) * 12;
}

function kindLabel(kind: string): string {
  return KIND_OPTIONS.find((k) => k.value === kind)?.label ?? kind;
}

function fmt(value: number, currency = "EUR"): string {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
  } catch { return `${currency} ${value.toFixed(2)}`; }
}

const INPUT = "w-full px-3 py-2 rounded-md text-sm bg-bg-card text-primary border border-border-subtle outline-none focus:border-accent transition-colors placeholder:text-muted";

export function OtherIncomeView() {
  const [incomes, setIncomes] = useState<Entity[]>([]);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<Mode>("view");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const selectedIdRef = useRef<number | null>(null);

  useEffect(() => { selectedIdRef.current = selected?.id ?? null; }, [selected]);
  useEffect(() => { load(); }, []);

  async function load(selectId?: number) {
    setLoading(true);
    setLoadFailed(false);
    const res = await rpc<Entity[]>("salary.get_other_incomes");
    setLoadFailed(!res.ok);
    if (res.ok && res.data) {
      setIncomes(res.data);
      const currentId = selectId ?? selectedIdRef.current;
      if (currentId != null) {
        setSelected(res.data.find((i) => i.id === currentId) || null);
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

  function selectIncome(i: Entity) {
    setSelected(i);
    setMode("view");
    setDeleteError(null);
    setSaveError(null);
  }

  async function handleSave(data: IncomeFormData) {
    setSaveError(null);
    const income: Record<string, unknown> = { ...data };
    if (mode === "edit" && selected) income.id = selected.id;
    const res = await rpc<Entity>("salary.save_other_income", income);
    if (res.ok) {
      setMode("view");
      await load(res.data?.id);
    } else {
      setSaveError(res.error || "Failed to save other income.");
    }
  }

  async function handleDelete(id: number) {
    setDeleteError(null);
    const res = await rpc("salary.delete_other_income", { income_id: id });
    if (res.ok) {
      setMode("view");
      await load();
    } else {
      setDeleteError(res.error || "Failed to delete other income.");
    }
  }

  const filtered = [...incomes]
    .sort((a, b) => str(a, "title").localeCompare(str(b, "title")))
    .filter((i) => {
      if (!search) return true;
      const q = search.toLowerCase();
      return str(i, "title").toLowerCase().includes(q) || str(i, "kind").toLowerCase().includes(q);
    });

  useAutoSelect(incomes, filtered, selected, setSelected, { enabled: mode === "view" });

  // Yearly total, one per currency.
  const yearlyTotals = new Map<string, number>();
  for (const i of incomes) {
    const cur = str(i, "currency") || "EUR";
    yearlyTotals.set(cur, (yearlyTotals.get(cur) ?? 0) + toYearly(num(i, "amount"), str(i, "period")));
  }

  return (
    <div className="flex flex-col h-full">
      <Toolbar
        title="Other Income"
        actions={<ToolbarButtonPrimary icon={<Plus size={13} />} label="New" onClick={startCreate} />}
        search={{ value: search, onChange: setSearch }}
      />

      {loadFailed && mode === "view" ? (
        <LoadError what="other income" onRetry={load} />
      ) : loading && incomes.length === 0 ? (
        <LoadingState />
      ) : incomes.length === 0 && mode === "view" ? (
        <EmptyStateIntro
          icon={Wallet}
          description="Add taxable income from outside your business, such as a part-time job or a pension. It is not revenue, but it puts your freelance income in a higher tax bracket, so Tuttle reserves the extra tax it causes."
        />
      ) : (
        <ListDetailLayout
          footer={
            <>
              {filtered.length} other income{filtered.length !== 1 ? "s" : ""}
              {incomes.length > 0 && (
                <span className="ml-2 text-tertiary">
                  · {Array.from(yearlyTotals, ([cur, total]) => `${fmt(total, cur)}/yr`).join(" + ")}
                </span>
              )}
            </>
          }
          list={
            filtered.length === 0 ? (
              <div className="p-4 text-sm text-center text-tertiary">No matches.</div>
            ) : (
              filtered.map((i) => (
                <IncomeRow
                  key={i.id}
                  income={i}
                  isSelected={selected?.id === i.id && mode !== "create"}
                  onSelect={() => selectIncome(i)}
                />
              ))
            )
          }
          detail={
            mode === "create" ? (
              <IncomeForm onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
            ) : mode === "edit" && selected ? (
              <IncomeForm income={selected} onSave={handleSave} onCancel={() => setMode("view")} error={saveError} />
            ) : selected ? (
              <IncomeDetail
                income={selected}
                onEdit={() => setMode("edit")}
                onDelete={() => handleDelete(selected.id)}
                deleteError={deleteError}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full gap-2 text-tertiary">
                <Wallet size={36} strokeWidth={1.2} />
                <span className="text-sm">Select an income</span>
              </div>
            )
          }
        />
      )}
    </div>
  );
}

/* ---------- List row ---------- */

function IncomeRow({ income, isSelected, onSelect }: {
  income: Entity; isSelected: boolean; onSelect: () => void;
}) {
  return (
    <button onClick={onSelect}
      className={`w-full text-left ${LIST_ROW_PADDING} border-b border-border-subtle transition-colors flex items-center gap-3
        ${isSelected ? "bg-bg-selected" : "hover:bg-bg-hover"}`}>
      <div className="w-9 h-9 rounded-full bg-bg-card flex items-center justify-center text-secondary shrink-0">
        <Wallet size={16} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium truncate">{str(income, "title")}</div>
        <div className="text-xs text-tertiary truncate">
          {fmt(num(income, "amount"), str(income, "currency"))} / {str(income, "period")} · {kindLabel(str(income, "kind"))}
        </div>
      </div>
    </button>
  );
}

/* ---------- Detail view ---------- */

function IncomeDetail({ income, onEdit, onDelete, deleteError }: {
  income: Entity; onEdit: () => void; onDelete: () => void; deleteError: string | null;
}) {
  const amount = num(income, "amount");
  const currency = str(income, "currency");
  const period = str(income, "period");

  return (
    <div className={`${DETAIL_PANE} space-y-6`}>
      <DetailHeader title={str(income, "title")}
        badges={
          <span className="inline-block text-xs font-medium px-2 py-0.5 rounded bg-accent/15 text-accent">
            {kindLabel(str(income, "kind"))}
          </span>
        }
        actions={<>
          <DetailAction label="Edit" onClick={onEdit} />
          <DetailDeleteAction key={income.id} label="Delete income" onDelete={onDelete} />
        </>} />

      {deleteError && (
        <div className="p-3 rounded-lg bg-status-danger/10 border border-status-danger/30 text-sm text-status-danger">{deleteError}</div>
      )}

      <DetailFields>
        <DetailField label="Amount">{fmt(amount, currency)}</DetailField>
        <DetailField label="Period">{period.charAt(0).toUpperCase() + period.slice(1)}</DetailField>
        <DetailField label="Per Year">{fmt(toYearly(amount, period), currency)}</DetailField>
        <DetailField label="Tax Treatment">
          Not business revenue. It sets the tax bracket of your freelance income: Tuttle reserves only the extra tax your
          freelance income causes on top of it.
        </DetailField>
      </DetailFields>
    </div>
  );
}

/* ---------- Form ---------- */

interface IncomeFormData {
  title: string;
  amount: number;
  currency: string;
  period: string;
  kind: string;
}

function IncomeForm({ income, onSave, onCancel, error }: {
  income?: Entity;
  onSave: (data: IncomeFormData) => void;
  onCancel: () => void;
  error?: string | null;
}) {
  const [title, setTitle] = useState(income ? str(income, "title") : "");
  const [amountStr, setAmountStr] = useState(income ? str(income, "amount") : "");
  const [currency, setCurrency] = useState(income ? str(income, "currency") : "");
  const [period, setPeriod] = useState(income ? str(income, "period") : "monthly");
  const [kind, setKind] = useState(income ? str(income, "kind") : "employment");
  const [saving, setSaving] = useState(false);

  // A new income starts in the primary currency.
  useEffect(() => {
    if (income) return;
    rpc<{ primary: string }>("settings.get_currency").then((res) => {
      const primary = res.ok ? res.data?.primary : undefined;
      setCurrency((current) => current || primary || "EUR");
    });
  }, [income]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    await onSave({ title, amount: parseFloat(amountStr) || 0, currency, period, kind });
    setSaving(false);
  }

  const canSave = title.trim() !== "" && amountStr.trim() !== "";

  return (
    <form onSubmit={handleSubmit} className={`${DETAIL_PANE} space-y-5`}>
      <DetailHeader title={income ? "Edit Other Income" : "New Other Income"}
        actions={<>
          <DetailAction label="Cancel" onClick={onCancel} />
          <DetailSubmit label={saving ? "Saving…" : "Save"} disabled={saving || !canSave} />
        </>} />

      <p className="text-xs text-muted"><span className="text-accent">*</span> Required</p>

      <div className="space-y-4">
        <div>
          <label className="block text-xs text-tertiary mb-1">Title<span className="text-accent ml-0.5">*</span></label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} autoFocus required
            placeholder="e.g. Part-time job" className={INPUT} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-tertiary mb-1">Taxable amount<span className="text-accent ml-0.5">*</span></label>
            <input type="number" step="0.01" min="0" value={amountStr} onChange={(e) => setAmountStr(e.target.value)}
              required placeholder="e.g. 2500.00" className={INPUT} />
          </div>
          <div>
            <label className="block text-xs text-tertiary mb-1">Currency<span className="text-accent ml-0.5">*</span></label>
            <input type="text" value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              required placeholder="EUR" className={INPUT} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-tertiary mb-1">Period</label>
            <select value={period} onChange={(e) => setPeriod(e.target.value)} className={INPUT}>
              {PERIOD_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-tertiary mb-1">Kind</label>
            <select value={kind} onChange={(e) => setKind(e.target.value)} className={INPUT}>
              {KIND_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          </div>
        </div>

        <p className="text-xs text-tertiary">
          Enter the taxable amount before tax, e.g. your gross salary. Its own tax is withheld or owed anyway, so Tuttle
          only reserves the extra tax your freelance income causes on top of it.
        </p>
      </div>

      {error && <p className="text-xs text-status-danger">{error}</p>}
    </form>
  );
}
