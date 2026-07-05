import { useEffect, useState, useCallback, useMemo } from "react";
import {
  Clock, Upload, Calendar, ChevronLeft, ChevronRight,
  FolderKanban, Trash2, MonitorSmartphone, Settings, RefreshCw,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { Toolbar, ToolbarButtonSecondary } from "../shared/ToolbarButtons";

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

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function TimeTrackingView() {
  const [calData, setCalData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [filterTag, setFilterTag] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [calendarSource, setCalendarSource] = useState<CalendarSource>(null);
  const [systemCals, setSystemCals] = useState<SystemCalendar[] | null>(null);
  const [sysCalAuthStatus, setSysCalAuthStatus] = useState<string | null>(null);
  const [sysCalLoading, setSysCalLoading] = useState(false);
  const [restoringSource, setRestoringSource] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [connectionLost, setConnectionLost] = useState(false);

  const isMac = typeof window !== "undefined" && window.tuttle?.platform === "darwin";

  const loadData = useCallback(async () => {
    setLoading(true);
    const calRes = await rpc<CalendarData>("timetracking.get_calendar_data", { year, month, project_tag: filterTag });
    if (calRes.ok && calRes.data) setCalData(calRes.data);
    setLoading(false);
  }, [year, month, filterTag]);

  useEffect(() => {
    (async () => {
      await rpc("timetracking.restore");
      const cfgRes = await rpc<{ source_type: string; has_data: boolean }>("timetracking.get_source_config");
      if (cfgRes.ok && cfgRes.data?.source_type && cfgRes.data.has_data) {
        setCalendarSource(cfgRes.data.source_type as CalendarSource);
        setConnectionLost(false);
      } else if (cfgRes.ok && cfgRes.data?.source_type && !cfgRes.data.has_data) {
        setCalendarSource(null);
        setConnectionLost(true);
      }
      setRestoringSource(false);
      loadData();
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (!restoringSource) loadData(); }, [loadData]); // eslint-disable-line react-hooks/exhaustive-deps

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

  // ── ICS drop ────────────────────────────────────────────────────────────

  async function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (!files.length) return;
    setImporting(true);
    setCalendarSource("ics");
    setConnectionLost(false);
    for (const file of Array.from(files)) {
      if (!file.name.endsWith(".ics")) continue;
      const buffer = await file.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = "";
      for (let i = 0; i < bytes.length; i += 8192) {
        binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
      }
      const b64 = btoa(binary);
      await rpc("timetracking.import_ics", { content: b64, name: file.name });
    }
    setImporting(false);
    loadData();
  }

  // ── macOS system calendar ───────────────────────────────────────────────

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
    setSystemCals(null);
    setCalendarSource("system");
    setConnectionLost(false);
    await rpc("timetracking.import_system_calendar", { calendar_id: calId });
    setImporting(false);
    loadData();
  }

  // ── Sync / clear ───────────────────────────────────────────────────────

  async function syncCalendar() {
    setSyncing(true);
    await rpc("timetracking.sync");
    await loadData();
    setSyncing(false);
  }

  async function clearData() {
    await rpc("timetracking.clear");
    setCalendarSource(null);
    setSelectedDay(null);
    setSystemCals(null);
    loadData();
  }

  // ── Derived data ────────────────────────────────────────────────────────

  const allTags = useMemo(() => {
    if (!calData) return [];
    return calData.projects.map((p) => p.tag);
  }, [calData]);

  const dayEvents = useMemo(() => {
    if (!selectedDay || !calData) return [];
    return calData.events.filter((ev) => ev.date === selectedDay);
  }, [selectedDay, calData]);

  const hasAnyData = calendarSource !== null;
  const monthHasEvents = calData && calData.summary && calData.summary.total_events > 0;

  // ── Render ──────────────────────────────────────────────────────────────

  if (loading && !calData) {
    return <div className="flex items-center justify-center h-full text-secondary">Loading time tracking…</div>;
  }

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Time Tracking"
        actions={hasAnyData ? <>
          <ToolbarButtonSecondary
            icon={<RefreshCw size={13} className={syncing ? "animate-spin" : ""} />}
            label={syncing ? "Syncing…" : "Sync"}
            onClick={syncCalendar} />
          <ToolbarButtonSecondary
            icon={<Trash2 size={13} />}
            label="Change source"
            onClick={clearData} />
        </> : undefined}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Main area */}
        <div className="flex-1 flex flex-col overflow-y-auto">
          {!hasAnyData ? (
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
          ) : (
            <>
              {/* Re-import strip — shows only the active source */}
              {calData && calendarSource === "ics" && (
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

              {/* Month navigation + grid */}
              {calData && (
              <div className="px-5 pt-4 pb-4">
                <div className="flex items-center gap-3 mb-4">
                  <button onClick={prevMonth} className="p-1.5 rounded-md hover:bg-bg-hover text-primary"><ChevronLeft size={18} /></button>
                  <h3 className="text-base font-bold min-w-[160px] text-center text-primary">
                    {MONTH_NAMES[month - 1]} {year}
                  </h3>
                  <button onClick={nextMonth} className="p-1.5 rounded-md hover:bg-bg-hover text-primary"><ChevronRight size={18} /></button>
                  <button onClick={goToday} className="text-xs font-medium text-secondary hover:text-primary hover:underline">Today</button>
                  <div className="flex-1" />
                  {/* Tag filter */}
                  {allTags.length > 1 && (
                    <div className="flex items-center gap-1">
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
                  calData={calData!}
                  allTags={allTags}
                  selectedDay={selectedDay}
                  onSelectDay={setSelectedDay}
                />
              </div>
              )}

              {/* Day detail */}
              {selectedDay && calData && (
                <DayDetail
                  day={selectedDay}
                  events={dayEvents}
                  allTags={allTags}
                  onClose={() => setSelectedDay(null)}
                />
              )}
            </>
          )}
        </div>

        {/* Right sidebar: project summary for current month */}
        {monthHasEvents && (
          <div className="w-60 shrink-0 border-l border-border-subtle overflow-y-auto p-4 space-y-4">
            <div className="text-[11px] font-bold uppercase tracking-wider text-primary mb-2">Projects</div>
            {calData!.projects.map((p) => (
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
                  <span className="text-xs tabular-nums font-medium text-primary">{p.hours}h</span>
                  <span className="text-[11px] text-secondary">{p.event_count} events</span>
                </div>
              </div>
            ))}

            <div className="border-t border-border-subtle pt-3">
              <div className="text-[11px] font-bold uppercase tracking-wider text-primary mb-1">Total</div>
              <div className="text-xl font-bold tabular-nums text-primary">{calData!.summary.total_hours}h</div>
              <div className="text-xs text-secondary">{calData!.summary.total_events} events</div>
              {calData!.summary.planned_hours > 0 && (
                <div className="text-xs text-blue-400 mt-1">
                  {calData!.summary.planned_hours}h planned
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Source chooser — exclusive choice between ICS file or system calendar
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
    <div className="flex flex-col items-center justify-center h-full gap-5 px-6">
      {connectionLost && (
        <div className="px-4 py-2.5 rounded-lg bg-warning/10 border border-warning/30 text-xs text-warning max-w-sm text-center leading-relaxed">
          Your calendar connection could not be restored. Please reconnect below.
        </div>
      )}
      <Clock size={40} strokeWidth={1.2} className="text-secondary" />
      <div className="max-w-md text-center space-y-2">
        <p className="text-sm text-tertiary">
          Time tracking records the hours you spend on projects, so you can generate accurate timesheets and invoices.
        </p>
        <p className="text-xs text-tertiary">
          Tuttle reads your calendar events and matches them to projects using hashtags in the event title (e.g. <code className="font-semibold text-primary">#myproject</code>).
        </p>
      </div>

      <div className="flex gap-4 w-full max-w-xl">
        {/* Option A: ICS file */}
        <div
          className={`flex-1 max-w-xs flex flex-col items-center gap-3 rounded-xl border-2 border-dashed p-8 transition-colors cursor-default ${dragOver ? "border-accent bg-accent/10" : "border-border-subtle hover:border-secondary"}`}
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
          <div className="flex-1 max-w-xs flex flex-col items-center gap-3 rounded-xl border-2 border-border-subtle p-8 transition-colors">
            <div className="w-12 h-12 rounded-2xl bg-bg-card flex items-center justify-center">
              <MonitorSmartphone size={22} strokeWidth={1.5} className="text-primary" />
            </div>
            <div className="text-center">
              <h4 className="text-sm font-semibold mb-1 text-primary">System Calendar</h4>
              <p className="text-xs text-secondary leading-relaxed">
                Connect directly to your system calendar.
              </p>
            </div>

            {/* Permission not granted */}
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

            {/* Calendar list */}
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

            {/* Connect button */}
            {!systemCals && (
              <button onClick={onLoadSystemCals} disabled={sysCalLoading}
                className="px-4 py-2 rounded-lg border border-border-subtle text-xs font-medium text-secondary hover:bg-bg-hover hover:text-primary transition-colors">
                {sysCalLoading ? "Loading…" : "Connect"}
              </button>
            )}
          </div>
        ) : (
          <div className="flex-1 max-w-xs flex flex-col items-center gap-3 rounded-xl border-2 border-border-subtle border-dashed p-8 opacity-60">
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
      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1">
        {WEEKDAYS.map((wd) => (
          <div key={wd} className="text-center text-[11px] font-bold uppercase tracking-wider text-secondary py-1.5">{wd}</div>
        ))}
      </div>

      {/* Day cells */}
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
// Day Detail
// ---------------------------------------------------------------------------

function DayDetail({
  day, events, allTags, onClose,
}: {
  day: string; events: TimeEvent[]; allTags: string[]; onClose: () => void;
}) {
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
    timedHours > 0 ? `${timedHours.toFixed(1)}h` : "",
  ].filter(Boolean).join(" + ") || "0h";

  return (
    <div className="mx-5 mt-4 mb-4 rounded-xl border border-border-subtle bg-bg-card shadow-sm">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <Calendar size={14} className="text-secondary" />
          <span className="text-sm font-bold text-primary">{dateLabel}</span>
          <span className="text-xs text-secondary font-medium tabular-nums">{totalLabel} total</span>
        </div>
        <button onClick={onClose} className="text-xs text-muted hover:text-secondary">close</button>
      </div>
      {events.length === 0 ? (
        <div className="px-3 py-4 text-sm text-muted text-center">No events on this day.</div>
      ) : (
        <div className="divide-y divide-border-subtle">
          {events.map((ev, i) => (
            <div key={i} className={`px-3 py-2 flex items-start gap-2.5 ${ev.is_future ? "opacity-70" : ""}`}>
              <div className="w-2.5 h-2.5 rounded-full mt-1 shrink-0"
                style={{
                  backgroundColor: ev.is_future ? "transparent" : tagColor(ev.tag, allTags),
                  border: ev.is_future ? `1.5px dashed ${tagColor(ev.tag, allTags)}` : "none",
                }} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{ev.title || "Untitled"}</span>
                  {ev.is_future && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 shrink-0">planned</span>
                  )}
                  {ev.tag && (
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full shrink-0"
                      style={{ color: tagColor(ev.tag, allTags), backgroundColor: tagColor(ev.tag, allTags) + "1F" }}>
                      {ev.tag}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-0.5 text-xs text-secondary">
                  {ev.all_day
                    ? <span>all day</span>
                    : <><span>{formatTime(ev.begin)} – {ev.end ? formatTime(ev.end) : "?"}</span>
                        <span className="tabular-nums font-medium">{ev.duration_hours}h</span></>
                  }
                </div>
                {ev.description && (
                  <p className="text-xs text-secondary mt-0.5 line-clamp-2">{ev.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
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

function formatDayDuration(info: DayInfo): string {
  const parts: string[] = [];
  if (info.all_day_count && info.all_day_count > 0)
    parts.push(`${info.all_day_count}d`);
  if (info.hours > 0) parts.push(`${info.hours}h`);
  return parts.join(" + ") || "0h";
}
