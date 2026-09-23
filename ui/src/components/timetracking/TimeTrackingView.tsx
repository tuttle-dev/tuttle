import { useEffect, useState, useCallback, useMemo } from "react";
import {
  AlertTriangle, Calendar, CalendarPlus, Check, ChevronLeft, ChevronRight, Clock,
  MonitorSmartphone, Pause, Pencil, Play, Plus, RefreshCw, Settings, Square, Trash2,
  Unplug, Upload, X,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { Toolbar, ToolbarButtonSecondary } from "../shared/ToolbarButtons";
import { useStatusBar } from "../shared/status-bar-context";
import { useNavigation } from "../shared/NavigationContext";
import { useTimer } from "./timer-context";
import { formatElapsed, formatHours } from "./format";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TimeEvent = {
  begin: string;
  end: string | null;
  duration_hours: number;
  title: string;
  tag: string;
  description: string;
  all_day: boolean;
  date: string;
  is_future: boolean;
  source: string;
  entry_id: number | null;
};

type DayInfo = { date: string; hours: number; all_day_count?: number; tags: string[]; count: number };

type CalendarData = {
  year: number;
  month: number;
  first_weekday: number;
  days_in_month: number;
  events: TimeEvent[];
  projects: { tag: string; title: string; hours: number; event_count: number }[];
  days: Record<string, DayInfo>;
  summary: { total_events: number; total_hours: number; planned_hours: number; planned_events: number };
};

type SystemCalendar = { id: string; title: string; source: string };

type CalendarSource = "ics" | "system" | null;

type SystemCalendarResult = {
  calendars: SystemCalendar[];
  auth_status: string;
};

type ProjectTag = { tag: string; title: string; id: number };

type EntryValues = { tag: string; title: string; start: string; end: string };

// ---------------------------------------------------------------------------
// Stable project colors
// ---------------------------------------------------------------------------

const PROJECT_COLORS = [
  "#0A84FF", "#30D158", "#FFD60A", "#BF5AF2",
  "#FF9F0A", "#FF375F", "#64D2FF", "#AC8E68",
];

function tagColor(tag: string, allTags: string[]): string {
  const idx = allTags.indexOf(tag);
  return PROJECT_COLORS[idx >= 0 ? idx % PROJECT_COLORS.length : 0];
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const inputCls =
  "px-2 py-1 rounded-md bg-bg-content border border-border-subtle text-xs text-primary placeholder:text-muted outline-none focus:border-accent";

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function TimeTrackingView() {
  const [calData, setCalData] = useState<CalendarData | null>(null);
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [filterTag, setFilterTag] = useState<string | null>(null);
  const [availableTags, setAvailableTags] = useState<string[]>([]);
  const [projectTags, setProjectTags] = useState<ProjectTag[]>([]);
  const [restoringSource, setRestoringSource] = useState(true);

  const [calendarSource, setCalendarSource] = useState<CalendarSource>(null);
  const [connectionLost, setConnectionLost] = useState(false);
  const [showSourceDialog, setShowSourceDialog] = useState(false);
  const [importing, setImporting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [systemCals, setSystemCals] = useState<SystemCalendar[] | null>(null);
  const [sysCalAuthStatus, setSysCalAuthStatus] = useState<string | null>(null);
  const [sysCalLoading, setSysCalLoading] = useState(false);

  const timer = useTimer();
  const { navigate } = useNavigation();
  const isMac = typeof window !== "undefined" && window.tuttle?.platform === "darwin";

  const loadData = useCallback(async () => {
    const res = await rpc<CalendarData>("timetracking.get_calendar_data", { year, month, project_tag: filterTag });
    if (res.ok && res.data) {
      setCalData(res.data);
      if (!filterTag) {
        const tags = res.data.projects.map((p) => p.tag);
        setAvailableTags((prev) =>
          prev.length === tags.length && prev.every((t, i) => t === tags[i]) ? prev : tags,
        );
      }
    }
  }, [year, month, filterTag]);

  useEffect(() => {
    (async () => {
      await rpc("timetracking.restore");
      const cfg = await rpc<{ source_type: string; has_data: boolean }>("timetracking.get_source_config");
      if (cfg.ok && cfg.data?.source_type) {
        if (cfg.data.has_data) setCalendarSource(cfg.data.source_type as CalendarSource);
        else setConnectionLost(true);
      }
      const tags = await rpc<ProjectTag[]>("timetracking.get_project_tags");
      if (tags.ok && tags.data) setProjectTags(tags.data);
      setRestoringSource(false);
    })();
  }, []);

  useEffect(() => {
    if (!restoringSource) loadData();
  }, [restoringSource, loadData, timer.entryVersion]);

  // ── Navigation ──────────────────────────────────────────────────────────

  function prevMonth() {
    if (month === 1) { setMonth(12); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
    setSelectedDay(null);
  }
  function nextMonth() {
    if (month === 12) { setMonth(1); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
    setSelectedDay(null);
  }
  function goToday() {
    const now = new Date();
    setYear(now.getFullYear());
    setMonth(now.getMonth() + 1);
    setSelectedDay(null);
  }

  // ── Calendar import ─────────────────────────────────────────────────────

  async function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (!files.length) return;
    setImporting(true);
    for (const file of Array.from(files)) {
      if (!file.name.endsWith(".ics")) continue;
      const buffer = await file.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = "";
      for (let i = 0; i < bytes.length; i += 8192) {
        binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      }
      await rpc("timetracking.import_ics", { content: btoa(binary), name: file.name });
    }
    setImporting(false);
    setCalendarSource("ics");
    setConnectionLost(false);
    setShowSourceDialog(false);
    loadData();
  }

  async function loadSystemCalendars() {
    setSysCalLoading(true);
    const res = await rpc<SystemCalendarResult>("timetracking.list_system_calendars");
    if (res.ok && res.data) {
      setSystemCals(res.data.calendars);
      setSysCalAuthStatus(res.data.auth_status);
    } else {
      setSystemCals([]);
    }
    setSysCalLoading(false);
  }

  async function openCalendarSettings() {
    await rpc("timetracking.list_system_calendars", { open_settings: true });
  }

  async function importSystemCalendar(calId: string) {
    setImporting(true);
    await rpc("timetracking.import_system_calendar", { calendar_id: calId });
    setImporting(false);
    setSystemCals(null);
    setCalendarSource("system");
    setConnectionLost(false);
    setShowSourceDialog(false);
    loadData();
  }

  async function syncCalendar() {
    setSyncing(true);
    await rpc("timetracking.sync");
    await loadData();
    setSyncing(false);
  }

  async function disconnectCalendar() {
    await rpc("timetracking.clear");
    setCalendarSource(null);
    setConnectionLost(false);
    setSystemCals(null);
    setFilterTag(null);
    setAvailableTags([]);
    loadData();
  }

  // ── Derived data ────────────────────────────────────────────────────────

  const allTags = useMemo(() => {
    if (availableTags.length > 0) return availableTags;
    return calData?.projects.map((p) => p.tag) ?? [];
  }, [calData, availableTags]);

  const dayEvents = useMemo(() => {
    if (!selectedDay || !calData) return [];
    return calData.events.filter((ev) => ev.date === selectedDay);
  }, [selectedDay, calData]);

  const monthHasEvents = !!calData && calData.summary.total_events > 0;
  const defaultTag = timer.state.tag || projectTags[0]?.tag || "";

  // ── Render ──────────────────────────────────────────────────────────────

  if (!calData) {
    return <div className="flex items-center justify-center h-full text-secondary">Loading time tracking…</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Time Tracking"
        actions={calendarSource ? (
          <>
            <ToolbarButtonSecondary
              icon={<RefreshCw size={13} className={syncing ? "animate-spin" : ""} />}
              label={syncing ? "Syncing…" : "Sync"}
              onClick={syncCalendar} />
            <ToolbarButtonSecondary
              icon={<Unplug size={13} />}
              label="Disconnect calendar"
              onClick={disconnectCalendar} />
          </>
        ) : (
          <ToolbarButtonSecondary
            icon={<CalendarPlus size={13} />}
            label="Import calendar"
            onClick={() => setShowSourceDialog(true)} />
        )}
      />

      <TimerBar projectTags={projectTags} onCreateProject={() => navigate("projects", {})} />

      {connectionLost && !calendarSource && (
        <div className="mx-5 mt-3 flex items-center gap-2 rounded-lg bg-status-warning/10 border border-status-warning/30 px-3 py-2 text-xs text-status-warning">
          <AlertTriangle size={13} className="shrink-0" />
          <span className="flex-1">Your calendar connection could not be restored.</span>
          <button onClick={() => setShowSourceDialog(true)} className="font-medium hover:underline">Reconnect</button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col overflow-y-auto">
          {calendarSource === "ics" && (
            <div
              className={`mx-5 mt-4 flex items-center gap-3 rounded-lg border border-dashed p-2.5 transition-colors ${dragOver ? "border-accent bg-accent/10" : "border-border-subtle"}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <Upload size={16} className="text-secondary shrink-0" />
              <span className="text-xs font-medium text-primary">
                Drop <code className="font-semibold text-primary">.ics</code> file to import more events
              </span>
              {importing && <span className="text-xs text-secondary animate-pulse">Importing…</span>}
            </div>
          )}

          <div className="px-5 pt-4 pb-4">
            <div className="flex items-center gap-3 mb-4">
              <button onClick={prevMonth} className="p-1.5 rounded-md hover:bg-bg-hover text-primary"><ChevronLeft size={18} /></button>
              <h3 className="text-base font-bold min-w-[160px] text-center text-primary">
                {MONTH_NAMES[month - 1]} {year}
              </h3>
              <button onClick={nextMonth} className="p-1.5 rounded-md hover:bg-bg-hover text-primary"><ChevronRight size={18} /></button>
              <button onClick={goToday} className="text-xs font-medium text-secondary hover:text-primary hover:underline">Today</button>
              <div className="flex-1" />
              {(availableTags.length > 1 || filterTag) && (
                <div className="flex items-center gap-1 flex-wrap justify-end">
                  <button
                    onClick={() => setFilterTag(null)}
                    className={`px-2 py-0.5 rounded-full text-[11px] font-medium transition-colors ${!filterTag ? "bg-accent text-white" : "text-tertiary hover:text-secondary"}`}
                  >All</button>
                  {allTags.map((t) => (
                    <button key={t} onClick={() => setFilterTag(t === filterTag ? null : t)}
                      className="px-2 py-0.5 rounded-full text-[11px] font-medium transition-colors"
                      style={{
                        backgroundColor: filterTag === t ? tagColor(t, allTags) : "transparent",
                        color: filterTag === t ? "#fff" : tagColor(t, allTags),
                        border: `1px solid ${tagColor(t, allTags)}44`,
                      }}
                    >{t}</button>
                  ))}
                </div>
              )}
            </div>

            <MonthGrid
              calData={calData}
              allTags={allTags}
              selectedDay={selectedDay}
              onSelectDay={setSelectedDay}
            />
          </div>

          {selectedDay && (
            <DayDetail
              key={selectedDay}
              day={selectedDay}
              events={dayEvents}
              allTags={allTags}
              projectTags={projectTags}
              defaultTag={defaultTag}
              onClose={() => setSelectedDay(null)}
              onDataChanged={loadData}
            />
          )}
        </div>

        {monthHasEvents && (
          <div className="w-60 shrink-0 border-l border-border-subtle overflow-y-auto p-4 space-y-4">
            <div className="text-[11px] font-bold uppercase tracking-wider text-primary mb-2">Projects</div>
            {calData.projects.map((p) => (
              <div key={p.tag} className="space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: tagColor(p.tag, allTags) }} />
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold truncate text-primary">{p.title || p.tag}</div>
                    {p.title && p.title !== p.tag && (
                      <div className="text-[11px] text-tertiary truncate">{p.tag}</div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-5">
                  <span className="text-xs tabular-nums font-medium text-primary">{formatHours(p.hours)}</span>
                  <span className="text-[11px] text-secondary">{p.event_count} {p.event_count === 1 ? "entry" : "entries"}</span>
                </div>
              </div>
            ))}

            <div className="border-t border-border-subtle pt-3">
              <div className="text-[11px] font-bold uppercase tracking-wider text-primary mb-1">Total</div>
              <div className="text-xl font-bold tabular-nums text-primary">{formatHours(calData.summary.total_hours)}</div>
              <div className="text-xs text-secondary">{calData.summary.total_events} {calData.summary.total_events === 1 ? "entry" : "entries"}</div>
              {calData.summary.planned_hours > 0 && (
                <div className="text-xs text-blue-400 mt-1">
                  {formatHours(calData.summary.planned_hours)} planned
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {showSourceDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowSourceDialog(false)}>
          <div className="bg-bg-content rounded-xl border border-border-subtle shadow-2xl w-[680px] max-h-[85vh] flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle shrink-0">
              <h2 className="text-base font-semibold text-primary">Import from calendar</h2>
              <button onClick={() => setShowSourceDialog(false)} className="p-1 rounded text-muted hover:text-primary hover:bg-bg-hover transition-colors">
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-5 py-5">
              <SourceChooser
                dragOver={dragOver}
                importing={importing}
                isMac={isMac}
                systemCals={systemCals}
                sysCalAuthStatus={sysCalAuthStatus}
                sysCalLoading={sysCalLoading}
                connectionLost={connectionLost}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onLoadSystemCals={loadSystemCalendars}
                onImportSystemCal={importSystemCalendar}
                onOpenSettings={openCalendarSettings}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Timer bar — the one control for tracking time live
// ---------------------------------------------------------------------------

function TimerBar({ projectTags, onCreateProject }: { projectTags: ProjectTag[]; onCreateProject: () => void }) {
  const timer = useTimer();
  const { status, elapsed, tag, title } = timer.state;
  const idle = status === "idle";
  const running = status === "running";
  const pending = status === "pending";
  const noProjects = projectTags.length === 0;

  const roundBtn = "w-9 h-9 rounded-full flex items-center justify-center text-white transition-opacity shrink-0 disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90";

  return (
    <div className={`mx-5 mt-4 rounded-xl border bg-bg-card shadow-sm transition-colors ${running ? "border-green-500/40" : pending ? "border-accent/40" : "border-border-subtle"}`}>
      <div className="flex items-center gap-3 px-4 py-2.5">
        {running
          ? <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse shrink-0" />
          : pending
            ? <Pause size={15} className="text-accent shrink-0" />
            : <Clock size={16} strokeWidth={1.8} className="text-tertiary shrink-0" />}
        <input
          type="text"
          value={title}
          onChange={(e) => timer.update({ title: e.target.value }, false)}
          onBlur={(e) => timer.update({ title: e.target.value })}
          onKeyDown={(e) => { if (e.key === "Enter" && idle && !noProjects) timer.start(); }}
          placeholder="What are you working on?"
          className="flex-1 min-w-0 bg-transparent text-sm text-primary placeholder:text-muted outline-none"
        />
        <select
          value={tag}
          onChange={(e) => timer.update({ tag: e.target.value })}
          disabled={noProjects}
          className={`max-w-[220px] px-2 py-1 rounded-md bg-bg-content border text-sm text-primary outline-none disabled:opacity-50 ${pending && !tag ? "border-accent ring-2 ring-accent/30" : "border-border-subtle"}`}
        >
          <option value="">{noProjects ? "No projects yet" : "No project"}</option>
          {projectTags.map((p) => (
            <option key={p.tag} value={p.tag}>{p.title}</option>
          ))}
        </select>
        <span className={`tabular-nums text-lg font-semibold min-w-[92px] text-right ${idle ? "text-tertiary" : "text-primary"}`}>
          {formatElapsed(elapsed)}
        </span>
        {idle && (
          <button onClick={() => timer.start()} disabled={noProjects} title="Start timer" className={`${roundBtn} bg-accent`}>
            <Play size={14} fill="currentColor" className="ml-0.5" />
          </button>
        )}
        {running && (
          <button onClick={() => timer.stop()} title="Stop timer" className={`${roundBtn} bg-red-500`}>
            <Square size={12} fill="currentColor" />
          </button>
        )}
        {pending && (
          <button onClick={() => timer.save()} disabled={!tag} title="Save entry" className={`${roundBtn} bg-accent`}>
            <Check size={16} />
          </button>
        )}
        {!idle && (
          <button onClick={() => timer.discard()} title="Discard timer"
            className="p-1 rounded text-muted hover:text-red-400 hover:bg-bg-hover transition-colors shrink-0">
            <X size={14} />
          </button>
        )}
      </div>
      {pending && (
        <div className="flex items-center gap-3 px-4 pb-2.5 text-xs">
          <span className="text-accent">
            {tag ? "Save this entry, or resume the timer." : "Choose a project to save this entry."}
          </span>
          <button onClick={timer.resume} className="text-secondary hover:text-primary hover:underline">Resume</button>
        </div>
      )}
      {noProjects && idle && (
        <div className="px-4 pb-2.5 text-xs text-secondary">
          Time is tracked per project.{" "}
          <button onClick={onCreateProject} className="text-accent hover:underline">Create a project</button>
          {" "}to start the timer.
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Source chooser — ICS file or system calendar (shown in a dialog)
// ---------------------------------------------------------------------------

function SourceChooser({
  dragOver, importing, isMac, systemCals, sysCalAuthStatus, sysCalLoading,
  connectionLost,
  onDragOver, onDragLeave, onDrop, onLoadSystemCals, onImportSystemCal, onOpenSettings,
}: {
  dragOver: boolean; importing: boolean; isMac: boolean;
  systemCals: SystemCalendar[] | null; sysCalAuthStatus: string | null;
  sysCalLoading: boolean;
  connectionLost: boolean;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent) => void;
  onLoadSystemCals: () => void;
  onImportSystemCal: (id: string) => void;
  onOpenSettings: () => void;
}) {
  const needsPermission = sysCalAuthStatus != null
    && sysCalAuthStatus !== "authorized"
    && sysCalAuthStatus !== "full_access";

  return (
    <div className="flex flex-col items-center gap-5">
      {connectionLost && (
        <div className="px-4 py-2.5 rounded-lg bg-status-warning/10 border border-status-warning/30 text-xs text-status-warning max-w-sm text-center leading-relaxed">
          Your calendar connection could not be restored. Please reconnect below.
        </div>
      )}
      <p className="max-w-md text-center text-xs text-tertiary leading-relaxed">
        Tuttle reads your calendar events and matches them to projects using hashtags in the event title
        (e.g. <code className="font-semibold text-primary">#myproject</code>).
      </p>

      <div className="flex gap-4 w-full">
        {/* Option A: ICS file */}
        <div
          className={`flex-1 flex flex-col items-center gap-3 rounded-xl border-2 border-dashed p-8 transition-colors cursor-default ${dragOver ? "border-accent bg-accent/10" : "border-border-subtle hover:border-secondary"}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          <div className="w-12 h-12 rounded-2xl bg-bg-card flex items-center justify-center">
            <Upload size={22} strokeWidth={1.5} className="text-primary" />
          </div>
          <div className="text-center">
            <h4 className="text-sm font-semibold mb-1 text-primary">ICS File Import</h4>
            <p className="text-xs text-secondary leading-relaxed">
              Drag and drop a <code className="font-medium text-primary">.ics</code> calendar export file here.
            </p>
          </div>
          {importing && (
            <div className="flex items-center gap-2 text-secondary text-sm">
              <div className="w-4 h-4 border-2 border-secondary border-t-transparent rounded-full animate-spin" />
              Importing…
            </div>
          )}
        </div>

        {/* Option B: System Calendar */}
        {isMac ? (
          <div className="flex-1 flex flex-col items-center gap-3 rounded-xl border-2 border-border-subtle p-8 transition-colors">
            <div className="w-12 h-12 rounded-2xl bg-bg-card flex items-center justify-center">
              <MonitorSmartphone size={22} strokeWidth={1.5} className="text-primary" />
            </div>
            <div className="text-center">
              <h4 className="text-sm font-semibold mb-1 text-primary">System Calendar</h4>
              <p className="text-xs text-secondary leading-relaxed">
                Connect directly to your system calendar.
              </p>
            </div>

            {systemCals && needsPermission && (
              <div className="text-center space-y-2">
                <p className="text-xs text-secondary">
                  Calendar access must be granted in System Settings.
                </p>
                <div className="flex gap-2 justify-center">
                  <button onClick={onOpenSettings}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-primary bg-bg-card hover:bg-bg-hover transition-colors">
                    <Settings size={12} />
                    Open Settings
                  </button>
                  <button onClick={onLoadSystemCals}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-primary bg-bg-card hover:bg-bg-hover transition-colors">
                    <RefreshCw size={12} />
                    Retry
                  </button>
                </div>
              </div>
            )}

            {systemCals && !needsPermission && systemCals.length > 0 && (
              <div className="w-full max-h-40 overflow-y-auto rounded-lg border border-border-subtle">
                {systemCals.map((cal) => (
                  <button key={cal.id} onClick={() => onImportSystemCal(cal.id)}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-bg-hover transition-colors flex items-center gap-2 border-b border-border-subtle last:border-0">
                    <Calendar size={12} className="text-secondary shrink-0" />
                    <span className="truncate text-primary">{cal.title}</span>
                    {cal.source && <span className="text-[10px] text-muted ml-auto shrink-0">{cal.source}</span>}
                  </button>
                ))}
              </div>
            )}

            {!systemCals && (
              <button onClick={onLoadSystemCals} disabled={sysCalLoading}
                className="px-4 py-2 rounded-lg border border-border-subtle text-xs font-medium text-secondary hover:bg-bg-hover hover:text-primary transition-colors">
                {sysCalLoading ? "Loading…" : "Connect"}
              </button>
            )}
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center gap-3 rounded-xl border-2 border-border-subtle border-dashed p-8 opacity-60">
            <div className="w-12 h-12 rounded-2xl bg-bg-card flex items-center justify-center">
              <MonitorSmartphone size={22} strokeWidth={1.5} className="text-tertiary" />
            </div>
            <div className="text-center">
              <h4 className="text-sm font-semibold mb-1 text-tertiary">System Calendar</h4>
              <p className="text-xs text-tertiary leading-relaxed">
                Not yet available on this platform.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Month Grid
// ---------------------------------------------------------------------------

function MonthGrid({
  calData, allTags, selectedDay, onSelectDay,
}: {
  calData: CalendarData; allTags: string[];
  selectedDay: string | null; onSelectDay: (d: string) => void;
}) {
  const { year, month, first_weekday, days_in_month, days } = calData;
  const todayStr = new Date().toISOString().slice(0, 10);

  const cells: (number | null)[] = [];
  for (let i = 0; i < first_weekday; i++) cells.push(null);
  for (let d = 1; d <= days_in_month; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <div>
      <div className="grid grid-cols-7 mb-1">
        {WEEKDAYS.map((wd) => (
          <div key={wd} className="text-center text-[11px] font-bold uppercase tracking-wider text-secondary py-1.5">{wd}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-px bg-border-subtle rounded-xl overflow-hidden border border-border-subtle shadow-sm">
        {cells.map((day, i) => {
          if (day === null) return <div key={`e${i}`} className="bg-bg-card min-h-[80px]" />;
          const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
          const info = days[dateStr];
          const isToday = dateStr === todayStr;
          const isSelected = dateStr === selectedDay;
          const dayOfWeek = (first_weekday + day - 1) % 7;
          const isWeekend = dayOfWeek >= 5;
          const isFuture = dateStr > todayStr;

          return (
            <button
              key={dateStr}
              onClick={() => onSelectDay(dateStr)}
              className={`bg-bg-card min-h-[80px] p-2 text-left transition-colors relative group
                ${isSelected ? "ring-2 ring-accent ring-inset bg-bg-selected" : "hover:bg-bg-hover"}
                ${isWeekend ? "opacity-60" : ""}
                ${isFuture && info ? "bg-blue-500/[0.03]" : ""}`}
            >
              <span className={`text-[13px] font-semibold ${isToday ? "bg-accent text-white px-1.5 py-0.5 rounded-full" : "text-primary"}`}>
                {day}
              </span>
              {info && (
                <div className="mt-1.5 space-y-1">
                  <div className="flex gap-1 flex-wrap">
                    {info.tags.map((t) => (
                      <div key={t} className="w-2.5 h-2.5 rounded-full"
                        style={{
                          backgroundColor: tagColor(t, allTags),
                          opacity: isFuture ? 0.5 : 1,
                          border: isFuture ? `1.5px dashed ${tagColor(t, allTags)}` : "none",
                        }}
                        title={`${t}${isFuture ? " (planned)" : ""}`}
                      />
                    ))}
                  </div>
                  <div className={`text-[11px] font-medium tabular-nums ${isFuture ? "text-blue-400/70" : "text-secondary"}`}>
                    {formatDayDuration(info)}
                  </div>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Entry form — shared by "add entry" and "edit entry" inside the day panel
// ---------------------------------------------------------------------------

function EntryForm({
  initial, projectTags, submitLabel, onSubmit, onCancel,
}: {
  initial: EntryValues; projectTags: ProjectTag[]; submitLabel: string;
  onSubmit: (values: EntryValues) => Promise<void>; onCancel: () => void;
}) {
  const [values, setValues] = useState<EntryValues>(initial);
  const [saving, setSaving] = useState(false);
  const valid = !!values.tag && !!values.start && !!values.end && values.end > values.start;

  async function submit() {
    if (!valid || saving) return;
    setSaving(true);
    await onSubmit(values);
    setSaving(false);
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <select value={values.tag} onChange={(e) => setValues({ ...values, tag: e.target.value })}
        className={`${inputCls} w-[170px]`}>
        <option value="" disabled>Project…</option>
        {projectTags.map((p) => <option key={p.tag} value={p.tag}>{p.title}</option>)}
      </select>
      <input type="time" value={values.start} onChange={(e) => setValues({ ...values, start: e.target.value })} className={inputCls} />
      <span className="text-xs text-muted">–</span>
      <input type="time" value={values.end} onChange={(e) => setValues({ ...values, end: e.target.value })} className={inputCls} />
      <input type="text" value={values.title} onChange={(e) => setValues({ ...values, title: e.target.value })}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder="Title (optional)" className={`${inputCls} flex-1 min-w-[140px]`} />
      <button onClick={submit} disabled={!valid || saving}
        className="px-2.5 py-1 rounded-md bg-accent text-white text-xs font-medium hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
        {submitLabel}
      </button>
      <button onClick={onCancel} className="px-2 py-1 text-xs text-muted hover:text-secondary transition-colors">Cancel</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Day Detail
// ---------------------------------------------------------------------------

function DayDetail({
  day, events, allTags, projectTags, defaultTag, onClose, onDataChanged,
}: {
  day: string; events: TimeEvent[]; allTags: string[];
  projectTags: ProjectTag[]; defaultTag: string;
  onClose: () => void; onDataChanged: () => void;
}) {
  const { showMessage } = useStatusBar();
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const dateLabel = (() => {
    try {
      return new Date(day + "T00:00:00").toLocaleDateString("en-US", {
        weekday: "long", month: "long", day: "numeric", year: "numeric",
      });
    } catch { return day; }
  })();

  const timedEvents = events.filter((e) => !e.all_day);
  const allDayEvents = events.filter((e) => e.all_day);
  const timedHours = timedEvents.reduce((sum, e) => sum + e.duration_hours, 0);
  const totalLabel = [
    allDayEvents.length > 0 ? `${allDayEvents.length}d` : "",
    timedHours > 0 ? formatHours(timedHours) : "",
  ].filter(Boolean).join(" + ") || "0m";

  async function addEntry(v: EntryValues) {
    const res = await rpc("timetracking.add_manual_entry", {
      tag: v.tag, title: v.title || null, date: day, start_time: v.start, end_time: v.end,
    });
    if (res.ok) {
      setAdding(false);
      onDataChanged();
    } else {
      showMessage(res.error || "The entry could not be added.", { type: "error" });
    }
  }

  async function updateEntry(ev: TimeEvent, v: EntryValues) {
    const res = await rpc("timetracking.update_manual_entry", {
      entry_id: ev.entry_id, tag: v.tag, title: v.title || null, date: day, start_time: v.start, end_time: v.end,
    });
    if (res.ok) {
      setEditing(null);
      onDataChanged();
    } else {
      showMessage(res.error || "The entry could not be updated.", { type: "error" });
    }
  }

  async function deleteEntry(ev: TimeEvent) {
    const res = await rpc("timetracking.delete_manual_entry", { entry_id: ev.entry_id });
    if (res.ok) {
      setDeleting(null);
      onDataChanged();
    } else {
      showMessage(res.error || "The entry could not be deleted.", { type: "error" });
    }
  }

  return (
    <div className="mx-5 mb-4 rounded-xl border border-border-subtle bg-bg-card shadow-sm">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <Calendar size={14} className="text-secondary" />
          <span className="text-sm font-bold text-primary">{dateLabel}</span>
          <span className="text-xs text-secondary font-medium tabular-nums">{totalLabel} total</span>
        </div>
        <button onClick={onClose} className="p-1 rounded text-muted hover:text-primary hover:bg-bg-hover transition-colors" title="Close">
          <X size={14} />
        </button>
      </div>

      {events.length === 0 ? (
        <div className="px-3 py-4 text-sm text-muted text-center">Nothing tracked on this day.</div>
      ) : (
        <div className="divide-y divide-border-subtle">
          {events.map((ev) => {
            const isManual = ev.entry_id != null;
            const key = isManual ? `m${ev.entry_id}` : `c${ev.begin}`;
            if (editing === key) {
              return (
                <div key={key} className="px-3 py-2.5 bg-bg-hover/40">
                  <EntryForm
                    initial={{ tag: ev.tag, title: ev.title, start: toTimeInput(ev.begin), end: ev.end ? toTimeInput(ev.end) : "" }}
                    projectTags={projectTags}
                    submitLabel="Save"
                    onSubmit={(v) => updateEntry(ev, v)}
                    onCancel={() => setEditing(null)}
                  />
                </div>
              );
            }
            return (
              <div key={key} className={`px-3 py-2 flex items-start gap-2.5 group ${ev.is_future ? "opacity-70" : ""}`}>
                <div className="w-2.5 h-2.5 rounded-full mt-1 shrink-0"
                  style={{
                    backgroundColor: ev.is_future ? "transparent" : tagColor(ev.tag, allTags),
                    border: ev.is_future ? `1.5px dashed ${tagColor(ev.tag, allTags)}` : "none",
                  }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium truncate ${ev.title ? "text-primary" : "text-muted"}`}>{ev.title || "No title"}</span>
                    {ev.is_future && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 shrink-0">planned</span>
                    )}
                    {ev.tag && (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full shrink-0"
                        style={{ color: tagColor(ev.tag, allTags), backgroundColor: tagColor(ev.tag, allTags) + "1F" }}>
                        {ev.tag}
                      </span>
                    )}
                    {!isManual && <span className="text-[10px] text-muted shrink-0">imported</span>}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 text-xs text-secondary">
                    {ev.all_day
                      ? <span>all day</span>
                      : <><span>{formatTime(ev.begin)} – {ev.end ? formatTime(ev.end) : "?"}</span>
                          <span className="tabular-nums font-medium">{formatHours(ev.duration_hours)}</span></>
                    }
                  </div>
                  {ev.description && (
                    <p className="text-xs text-secondary mt-0.5 line-clamp-2">{ev.description}</p>
                  )}
                  {deleting === key && (
                    <div className="mt-1.5 flex items-center gap-2 text-xs">
                      <span className="text-red-400">Delete this entry?</span>
                      <button onClick={() => deleteEntry(ev)} className="font-medium text-red-400 hover:underline">Delete</button>
                      <button onClick={() => setDeleting(null)} className="text-muted hover:text-secondary">Cancel</button>
                    </div>
                  )}
                </div>
                {isManual && deleting !== key && (
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <button onClick={() => { setEditing(key); setAdding(false); }}
                      className="p-1 rounded text-muted hover:text-primary hover:bg-bg-hover transition-colors" title="Edit">
                      <Pencil size={12} />
                    </button>
                    <button onClick={() => setDeleting(key)}
                      className="p-1 rounded text-muted hover:text-red-400 hover:bg-bg-hover transition-colors" title="Delete">
                      <Trash2 size={12} />
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="px-3 py-2 border-t border-border-subtle">
        {adding ? (
          <EntryForm
            initial={{ tag: defaultTag, title: "", start: "09:00", end: "17:00" }}
            projectTags={projectTags}
            submitLabel="Add"
            onSubmit={addEntry}
            onCancel={() => setAdding(false)}
          />
        ) : (
          <button onClick={() => { setAdding(true); setEditing(null); }}
            disabled={projectTags.length === 0}
            className="flex items-center gap-1 text-xs font-medium text-accent hover:underline disabled:opacity-40 disabled:no-underline">
            <Plus size={12} />
            Add entry
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
  } catch { return ""; }
}

function toTimeInput(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatDayDuration(info: DayInfo): string {
  const parts: string[] = [];
  if (info.all_day_count && info.all_day_count > 0)
    parts.push(`${info.all_day_count}d`);
  if (info.hours > 0) parts.push(formatHours(info.hours));
  return parts.join(" + ") || "0m";
}
