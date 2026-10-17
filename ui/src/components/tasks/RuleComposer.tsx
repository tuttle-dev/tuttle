import { useEffect, useRef, useState } from "react";
import { CalendarDays, Trash2, Zap } from "lucide-react";
import { rpc } from "../../api/rpc";
import { useDismiss } from "../../hooks/useDismiss";
import {
  REPEATS, findEvent, fmtDay, newRule, repeatOf, suggestedTitle, unitLabel,
  type RuleKind, type RuleOptions, type RulePreview, type TaskRule,
} from "./rules";

type Timing = "on" | "before" | "after";

const KINDS: { kind: RuleKind; icon: typeof Zap; label: string; hint: string }[] = [
  { kind: "date", icon: CalendarDays, label: "On a date", hint: "Once or repeating" },
  { kind: "event", icon: Zap, label: "When something happens", hint: "Around a contract, project, invoice or goal" },
];

// Each blank in the trigger sentence is an inline word, sized to its text.
const WORD = "appearance-none field-sizing-content font-semibold leading-normal text-accent bg-accent/12 hover:bg-accent/20 rounded-md px-[5px] py-px outline-none focus-visible:ring-2 focus-visible:ring-accent cursor-pointer";
const SELECT = `${WORD} word-select pr-[16px]`;

function timingOf(rule: TaskRule): Timing {
  if (rule.offset === 0) return "on";
  return rule.before ? "before" : "after";
}

/** Create or edit a task rule. The trigger reads as one sentence; a preview shows what it would do. */
export function RuleComposer({ rule, options, onClose, onSaved, onDeleted }: {
  rule: TaskRule | null;
  options: RuleOptions;
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  const editing = rule?.id != null;
  const [draft, setDraft] = useState<TaskRule>(() => rule ?? newRule("date", options));
  const [timing, setTiming] = useState<Timing>(() => timingOf(rule ?? newRule("event", options)));
  // The amount as typed, so it can be cleared and retyped; it counts as at least 1.
  const [offsetText, setOffsetText] = useState(() => String(rule && rule.offset > 0 ? rule.offset : 2));
  const offset = Math.max(1, parseInt(offsetText) || 1);
  const [titleTouched, setTitleTouched] = useState(editing);
  // The preview, with the trigger it was worked out for: one for another trigger is never shown.
  const [preview, setPreview] = useState<{ trigger: string; data: RulePreview } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const backdrop = useDismiss(onClose);

  const found = findEvent(options, draft.event);
  const record = found?.record ?? options.records[0];
  const event = found?.event ?? record.events[0];
  const repeat = repeatOf(draft);

  /** The rule as it would be saved. */
  function payload(d: TaskRule = draft, t: Timing = timing, o: number = offset): TaskRule {
    if (d.kind === "date") return { ...d, event: null, client_id: null };
    return { ...d, offset: t === "on" ? 0 : o, before: t === "before" };
  }

  function update(patch: Partial<TaskRule>, nextTiming: Timing = timing) {
    setDraft((d) => {
      const next = { ...d, ...patch };
      if (!titleTouched) next.title = suggestedTitle(payload(next, nextTiming), options);
      return next;
    });
  }

  function changeTiming(t: Timing) {
    setTiming(t);
    update({}, t);
  }

  function changeRecord(key: string) {
    const rec = options.records.find((r) => r.key === key);
    if (!rec) return;
    const first = rec.events.find((e) => !e.state) ?? rec.events[0];
    const t = first.after_only && timing === "before" ? "after" : timing;
    setTiming(t);
    update({ event: first.key, client_id: rec.key === "goal" ? null : draft.client_id }, t);
  }

  function changeEvent(key: string) {
    const ev = record.events.find((e) => e.key === key);
    const t = ev?.after_only && timing === "before" ? "after" : timing;
    setTiming(t);
    update({ event: key }, t);
  }

  function changeKind(kind: RuleKind) {
    if (kind === draft.kind) return;
    // A rule switched from the other kind brings none of this kind's fields.
    const fresh = newRule(kind, options);
    if (kind === "event" && !draft.event) update({ kind, event: fresh.event, offset_unit: fresh.offset_unit });
    else if (kind === "date" && !draft.start_date) update({ kind, start_date: fresh.start_date, unit: fresh.unit, every: fresh.every });
    else update({ kind });
  }

  function insertPlaceholder(name: string) {
    const input = titleRef.current;
    const token = `{${name}}`;
    const start = input?.selectionStart ?? draft.title.length;
    const end = input?.selectionEnd ?? start;
    setTitleTouched(true);
    setDraft((d) => ({ ...d, title: d.title.slice(0, start) + token + d.title.slice(end) }));
    requestAnimationFrame(() => {
      input?.focus();
      input?.setSelectionRange(start + token.length, start + token.length);
    });
  }

  /** What decides which tasks the rule makes; the title only words them. */
  function triggerOf(r: TaskRule): string {
    const { title: _title, note: _note, ...trigger } = r;
    return JSON.stringify(trigger);
  }

  // Preview what the rule would do, a moment after each change.
  useEffect(() => {
    let stale = false;
    const rule = payload();
    const handle = setTimeout(async () => {
      const res = await rpc<RulePreview>("tasks.preview_rule", { rule: rule as unknown as Record<string, unknown> });
      if (!stale) setPreview({ trigger: triggerOf(rule), data: res.ok ? res.data : { error: res.error ?? "Couldn't preview the rule." } });
    }, 150);
    return () => { stale = true; clearTimeout(handle); };
  }, [draft, timing, offset]); // eslint-disable-line react-hooks/exhaustive-deps

  async function save() {
    setSaving(true);
    setError(null);
    const res = await rpc("tasks.save_rule", { rule: payload() as unknown as Record<string, unknown> });
    setSaving(false);
    if (res.ok) onSaved();
    else setError(res.error ?? "Couldn't save the rule.");
  }

  async function remove() {
    if (draft.id == null) return;
    const res = await rpc("tasks.delete_rule", { id: draft.id });
    if (res.ok) onDeleted();
    else setError(res.error ?? "Couldn't delete the rule.");
  }

  const placeholders = draft.kind === "date" ? ["period", "date"] : record.placeholders;
  const timings: { value: Timing; label: string }[] = [
    { value: "on", label: event.state ? "as soon as" : "on the day" },
    ...(event.after_only ? [] : [{ value: "before" as Timing, label: "before" }]),
    { value: "after", label: "after" },
  ];
  const capitalize = (s: string) => s[0].toUpperCase() + s.slice(1);
  const dateEvents = record.events.filter((e) => !e.state);
  const stateEvents = record.events.filter((e) => e.state);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" {...backdrop}>
      <div role="dialog" aria-modal="true" aria-labelledby="rule-composer-title"
        className="bg-bg-content rounded-xl border border-border-subtle shadow-2xl w-[700px] max-w-full max-h-[85vh] flex flex-col overflow-hidden">
        <div className="px-5 py-4 border-b border-border-subtle shrink-0">
          <h2 id="rule-composer-title" className="text-base font-semibold">{editing ? "Edit rule" : "New rule"}</h2>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          <div className="grid grid-cols-2 gap-2">
            {KINDS.map(({ kind, icon: Icon, label, hint }) => (
              <button key={kind} type="button" onClick={() => changeKind(kind)} aria-pressed={draft.kind === kind}
                className={`flex flex-col items-start gap-1 rounded-lg border px-3 py-2.5 text-left transition-colors
                  ${draft.kind === kind ? "border-accent bg-accent/12 text-accent" : "border-border-subtle text-tertiary hover:border-border"}`}>
                <Icon size={15} />
                <span className={`text-sm font-semibold ${draft.kind === kind ? "text-primary" : "text-secondary"}`}>{label}</span>
                <span className="text-[11px] leading-snug">{hint}</span>
              </button>
            ))}
          </div>

          <div className="rounded-lg bg-bg-card px-3.5 py-2.5 text-[15px] leading-[2.2] text-secondary">
            {draft.kind === "date" ? (
              <>
                <select aria-label="Repeat" className={SELECT} value={repeat?.key ?? "custom"}
                  onChange={(e) => {
                    const r = REPEATS.find((x) => x.key === e.target.value);
                    if (r) update({ unit: r.unit, every: r.every });
                  }}>
                  {!repeat && <option value="custom">Every {draft.every} {unitLabel(draft.unit ?? "month", draft.every)}</option>}
                  {REPEATS.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
                </select>{" "}
                {draft.unit ? "starting" : "on"}{" "}
                <input type="date" aria-label="Date" className={`${WORD} w-[9.5em]`} value={draft.start_date ?? ""}
                  onChange={(e) => update({ start_date: e.target.value || null })} />
              </>
            ) : (
              <>
                {timing !== "on" && (
                  <>
                    <input type="number" min={1} aria-label="How many" value={offsetText}
                      onChange={(e) => setOffsetText(e.target.value)} onBlur={() => setOffsetText(String(offset))}
                      className={`${WORD} min-w-[2.2em] text-center tabular-nums cursor-text [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none`} />{" "}
                    <select aria-label="Unit" className={SELECT} value={draft.offset_unit}
                      onChange={(e) => update({ offset_unit: e.target.value as TaskRule["offset_unit"] })}>
                      {(["day", "week", "month"] as const).map((u) => <option key={u} value={u}>{unitLabel(u, offset)}</option>)}
                    </select>{" "}
                  </>
                )}
                <select aria-label="When" className={SELECT} value={timing} onChange={(e) => changeTiming(e.target.value as Timing)}>
                  {timings.map((t) => <option key={t.value} value={t.value}>{timing === "on" ? capitalize(t.label) : t.label}</option>)}
                </select>{" "}
                <select aria-label="What" className={SELECT} value={record.key} onChange={(e) => changeRecord(e.target.value)}>
                  {options.records.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
                </select>{" "}
                <select aria-label="Happens" className={SELECT} value={event.key} onChange={(e) => changeEvent(e.target.value)}>
                  {dateEvents.length > 0 && (
                    <optgroup label="Dates">
                      {dateEvents.map((ev) => <option key={ev.key} value={ev.key}>{ev.label}</option>)}
                    </optgroup>
                  )}
                  {stateEvents.length > 0 && (
                    <optgroup label="Status changes">
                      {stateEvents.map((ev) => <option key={ev.key} value={ev.key}>{ev.label}</option>)}
                    </optgroup>
                  )}
                </select>
                {record.key !== "goal" && options.clients.length > 0 && (
                  <>
                    {" "}
                    {/* A long client name wraps as a whole, after the event. */}
                    <span className="whitespace-nowrap">
                      for{" "}
                      <select aria-label="Client" className={SELECT} value={draft.client_id ?? ""}
                        onChange={(e) => update({ client_id: e.target.value ? Number(e.target.value) : null })}>
                        <option value="">any client</option>
                        {options.clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                      </select>
                    </span>
                  </>
                )}
              </>
            )}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="rule-title" className="text-xs font-semibold text-secondary uppercase tracking-wider">Task</label>
            <input id="rule-title" ref={titleRef} value={draft.title} autoComplete="off" placeholder="What should you do?"
              onChange={(e) => { setTitleTouched(true); setDraft((d) => ({ ...d, title: e.target.value })); }}
              className="w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary outline-none focus:border-accent" />
            <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
              <span>Insert</span>
              {placeholders.map((p) => (
                <button key={p} type="button" onClick={() => insertPlaceholder(p)}
                  className="px-1.5 rounded border border-accent/35 bg-accent/12 text-accent hover:bg-accent hover:text-on-fill transition-colors">
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="rule-note" className="text-xs font-semibold text-secondary uppercase tracking-wider">
              Note <span className="normal-case tracking-normal font-normal text-muted">optional</span>
            </label>
            <input id="rule-note" value={draft.note ?? ""} autoComplete="off" placeholder="Shown under the task"
              onChange={(e) => setDraft((d) => ({ ...d, note: e.target.value }))}
              className="w-full px-3 py-1.5 rounded-md bg-bg-card border border-border-subtle text-sm text-primary outline-none focus:border-accent" />
          </div>

          <RulePreviewBox
            preview={preview && preview.trigger === triggerOf(payload()) ? preview.data : null}
            kind={draft.kind}
            watch={{
              noun: record.label.replace(/^(a|an) /, ""),
              event: event.label,
              later: timing === "on" ? "" : ` ${offset} ${unitLabel(draft.offset_unit, offset)} later`,
            }} />
        </div>

        <div className="px-5 py-3 border-t border-border-subtle flex items-center gap-2 shrink-0">
          {editing && !confirmDelete && (
            <button type="button" onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-status-danger hover:bg-bg-hover transition-colors">
              <Trash2 size={14} /> Delete rule
            </button>
          )}
          {editing && confirmDelete && (
            <div className="flex items-center gap-1.5 text-sm">
              <span className="text-secondary">Delete it and its tasks?</span>
              <button type="button" onClick={remove}
                className="px-2 py-1 rounded bg-status-danger/10 text-status-danger hover:bg-status-danger/20 transition-colors">Delete</button>
              <button type="button" onClick={() => setConfirmDelete(false)}
                className="px-2 py-1 rounded text-muted hover:text-secondary transition-colors">Keep</button>
            </div>
          )}
          {error && <p className="text-xs text-status-danger flex-1 text-right">{error}</p>}
          <button type="button" onClick={onClose}
            className={`${error ? "" : "ml-auto"} px-4 py-1.5 rounded-md text-sm text-secondary hover:text-primary hover:bg-bg-hover transition-colors`}>
            Cancel
          </button>
          {/* The preview says what's missing; the rule can be saved once it doesn't. */}
          <button type="button" onClick={save} disabled={saving || !draft.title.trim() || !!preview?.data.error}
            className="px-4 py-1.5 rounded-md text-sm font-medium bg-accent text-on-fill hover:bg-accent/90 transition-colors disabled:opacity-50">
            {saving ? "Saving…" : editing ? "Save rule" : "Create rule"}
          </button>
        </div>
      </div>
    </div>
  );
}

function PreviewRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3 items-baseline text-sm">
      <span className="w-12 shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted">{label}</span>
      <div className="flex-1 min-w-0 flex flex-col gap-0.5">{children}</div>
    </div>
  );
}

/** The rule's event, for the preview of a new rule on a final status: "invoice", "is paid", " 1 week later". */
type Watch = { noun: string; event: string; later: string };

function RulePreviewBox({ preview, kind, watch }: { preview: RulePreview | null; kind: RuleKind; watch: Watch }) {
  let body: React.ReactNode;
  if (!preview) body = <p className="text-xs text-muted">Working out what this rule does…</p>;
  else if (preview.error) body = <p className="text-xs text-tertiary">{preview.error}</p>;
  else if (preview.from_today) {
    body = <p className="text-sm text-primary">From today, each {watch.noun} that {watch.event} gets a task{watch.later}.</p>;
  } else {
    const now = preview.now ?? [];
    body = (
      <>
        {now.length > 0 && (
          <PreviewRow label="Today">
            {now.slice(0, 3).map((t, i) => <span key={i} className="text-primary">{t.title}</span>)}
            {now.length > 3 && <span className="text-xs text-tertiary">and {now.length - 3} more</span>}
          </PreviewRow>
        )}
        {preview.next && (
          <PreviewRow label="Next">
            <span className="text-primary">{preview.next.title}</span>
            <span className="text-xs text-tertiary tabular-nums">Appears {fmtDay(preview.next.date, true)}</span>
          </PreviewRow>
        )}
        {preview.later && preview.later.length > 0 && (
          <PreviewRow label="Then">
            <span className="text-xs text-tertiary tabular-nums">{preview.later.join(", ")}, …</span>
          </PreviewRow>
        )}
        {now.length === 0 && !preview.next && (
          <p className="text-xs text-tertiary">
            {kind === "date"
              ? "That date has passed. Choose today or a later date."
              : "Nothing in your records matches yet. Tasks appear as soon as something does."}
          </p>
        )}
      </>
    );
  }
  return <div aria-live="polite" className="rounded-lg border border-border-subtle px-3.5 py-3 space-y-2">{body}</div>;
}
