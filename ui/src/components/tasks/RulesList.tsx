import { CalendarDays, Plus, Repeat, Zap } from "lucide-react";
import { fmtDay, ruleSentence, type RuleOptions, type TaskRule } from "./rules";

const GROUPS: { kind: TaskRule["kind"]; label: string }[] = [
  { kind: "date", label: "On a date" },
  { kind: "event", label: "When something happens" },
];

/** The rules that create tasks, each read as its sentence over the task it makes. */
export function RulesList({ rules, options, onEdit, onNew, onTogglePause }: {
  rules: TaskRule[];
  options: RuleOptions | null;
  onEdit: (rule: TaskRule) => void;
  onNew: () => void;
  onTogglePause: (rule: TaskRule) => void;
}) {
  return (
    <div className="space-y-6">
      {GROUPS.map(({ kind, label }) => {
        const group = rules.filter((r) => r.kind === kind);
        if (group.length === 0) return null;
        return (
          <div key={kind} className="space-y-2">
            <h2 className="text-xs font-medium uppercase tracking-wide text-tertiary">{label}</h2>
            {group.map((rule) => (
              <RuleRow key={rule.id} rule={rule} options={options} onEdit={() => onEdit(rule)} onTogglePause={() => onTogglePause(rule)} />
            ))}
          </div>
        );
      })}
      <button type="button" onClick={onNew}
        className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-lg border border-dashed border-border text-sm font-medium text-tertiary hover:text-accent hover:border-accent hover:bg-accent/10 transition-colors">
        <Plus size={14} /> New rule
      </button>
    </div>
  );
}

function RuleRow({ rule, options, onEdit, onTogglePause }: {
  rule: TaskRule;
  options: RuleOptions | null;
  onEdit: () => void;
  onTogglePause: () => void;
}) {
  const Icon = rule.kind === "event" ? Zap : rule.unit ? Repeat : CalendarDays;
  const status = rule.paused ? "Paused"
    : rule.next_date ? `Next ${fmtDay(rule.next_date)}`
    : rule.kind === "event" && rule.event?.includes("=") ? "Watching"
    : "";
  return (
    <div role="button" tabIndex={0} onClick={onEdit}
      onKeyDown={(e) => { if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onEdit(); } }}
      className="flex items-center gap-3 rounded-lg border border-border-subtle bg-bg-content px-3.5 py-2.5 cursor-pointer hover:border-border hover:bg-bg-sidebar transition-colors">
      <div className="w-7 h-7 shrink-0 rounded-md bg-bg-card grid place-items-center text-tertiary">
        <Icon size={15} />
      </div>
      <div className={`flex-1 min-w-0 ${rule.paused ? "opacity-50" : ""}`}>
        <div className="text-sm font-medium text-primary">{ruleSentence(rule, options)}</div>
        <div className="text-sm text-tertiary break-words"><TemplateText text={rule.title} /></div>
      </div>
      {status && <span className="shrink-0 text-xs text-muted whitespace-nowrap tabular-nums">{status}</span>}
      <Switch on={!rule.paused} label={rule.paused ? "Resume rule" : "Pause rule"} onToggle={onTogglePause} />
    </div>
  );
}

/** A task title template, with its {placeholders} shown as tokens. */
export function TemplateText({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\{\w+\})/).map((part, i) =>
        /^\{\w+\}$/.test(part)
          ? <span key={i} className="text-xs text-accent bg-accent/12 rounded px-1 whitespace-nowrap">{part.slice(1, -1)}</span>
          : <span key={i}>{part}</span>,
      )}
    </>
  );
}

function Switch({ on, label, onToggle }: { on: boolean; label: string; onToggle: () => void }) {
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label} title={label}
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      className={`relative shrink-0 w-[30px] h-[18px] rounded-full transition-colors ${on ? "bg-status-success" : "bg-border"}`}>
      <span className={`absolute top-[2px] left-[2px] w-[14px] h-[14px] rounded-full bg-white shadow transition-transform ${on ? "translate-x-[12px]" : ""}`} />
    </button>
  );
}
