import { useEffect, useState, useMemo } from "react";
import {
  FileText, FileSignature, FolderKanban, Flag,
  ListFilter, CalendarDays,
} from "lucide-react";
import { rpc } from "../../api/rpc";
import { Toolbar, ToolbarFilterGroup } from "../shared/ToolbarButtons";
import { EmptyStateIntro } from "../shared/EmptyStateIntro";
import type { Entity } from "../../api/types";
import { str, bool } from "../../api/entity";

type Category = "all" | "invoice" | "contract" | "project" | "goal";

const CATEGORIES: { id: Category; label: string; icon: typeof FileText }[] = [
  { id: "all",      label: "All",       icon: ListFilter },
  { id: "invoice",  label: "Invoices",  icon: FileText },
  { id: "contract", label: "Contracts", icon: FileSignature },
  { id: "project",  label: "Projects",  icon: FolderKanban },
  { id: "goal",     label: "Goals",     icon: Flag },
];

const CATEGORY_COLORS: Record<string, string> = {
  all:      "var(--color-status-info)",
  invoice:  "var(--color-status-info)",
  contract: "var(--color-status-success)",
  project:  "var(--color-status-warning)",
  goal:     "#BF5AF2",
};

const FILTER_OPTIONS = ["all", "invoice", "contract", "project", "goal"] as const;
const FILTER_LABELS: Record<string, string> = { all: "All", invoice: "Invoices", contract: "Contracts", project: "Projects", goal: "Goals" };
const FILTER_ICONS: Record<string, React.ReactNode> = {
  all: <ListFilter size={12} />, invoice: <FileText size={12} />,
  contract: <FileSignature size={12} />, project: <FolderKanban size={12} />, goal: <Flag size={12} />,
};

function dotColor(event: Entity): string {
  const title = str(event, "title").toLowerCase();
  if (title.includes("reminder") && title.includes("sent")) return "var(--color-status-warning)";
  if (title.includes("paid") || title.includes("completed") || title.includes("reached")) return "var(--color-status-success)";
  if (title.includes("overdue") || title.includes("cancelled")) return "var(--color-status-danger)";
  if (title.includes("reminder")) return "var(--color-status-warning)";
  if (title.includes("due")) return CATEGORY_COLORS[str(event, "category")] || "var(--color-status-info)";
  return CATEGORY_COLORS[str(event, "category")] || "var(--color-status-info)";
}

function formatDate(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch { return iso; }
}

function monthKey(iso: string): string {
  return iso?.slice(0, 7) || "";
}

function monthLabel(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso + "-01").toLocaleDateString("en-US", { month: "long", year: "numeric" });
  } catch { return iso; }
}

type EventGroup = { key: string; label: string; events: Entity[] };

export function TimelineView() {
  const [events, setEvents] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<Category>("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    const res = await rpc<Entity[]>("timeline.get_events", {});
    if (res.ok && res.data) setEvents(res.data);
    setLoading(false);
  }

  const filtered = useMemo(() => {
    let result = events;
    if (activeFilter !== "all") {
      result = result.filter((e) => str(e, "category") === activeFilter);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (e) => str(e, "title").toLowerCase().includes(q)
          || str(e, "description").toLowerCase().includes(q),
      );
    }
    return result;
  }, [events, activeFilter, searchQuery]);

  const groups = useMemo<EventGroup[]>(() => {
    const result: EventGroup[] = [];
    let currentKey = "";
    let current: Entity[] = [];
    for (const ev of filtered) {
      const k = monthKey(str(ev, "date"));
      if (k !== currentKey) {
        if (current.length) result.push({ key: currentKey, label: monthLabel(currentKey), events: current });
        currentKey = k;
        current = [ev];
      } else {
        current.push(ev);
      }
    }
    if (current.length) result.push({ key: currentKey, label: monthLabel(currentKey), events: current });
    return result;
  }, [filtered]);

  const todayISO = new Date().toISOString().slice(0, 10);

  const todayPosition = useMemo<{ group: number; event: number } | null>(() => {
    for (let gi = 0; gi < groups.length; gi++) {
      for (let ei = 0; ei < groups[gi].events.length; ei++) {
        const ev = groups[gi].events[ei];
        if (!bool(ev, "is_future") && str(ev, "date") <= todayISO) {
          return { group: gi, event: ei };
        }
      }
    }
    return null;
  }, [groups, todayISO]);

  if (loading) return <div className="flex items-center justify-center h-full text-secondary">Loading timeline…</div>;

  if (!events.length) {
    return (
      <div className="flex flex-col h-full">
        <Toolbar title="Timeline" />
        <EmptyStateIntro icon={CalendarDays} description="Key events — new contracts, sent invoices, and project milestones — appear here in chronological order." />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Toolbar title="Timeline"
        center={<ToolbarFilterGroup options={FILTER_OPTIONS} value={activeFilter} onChange={setActiveFilter}
          colors={CATEGORY_COLORS} icons={FILTER_ICONS} labels={FILTER_LABELS} />}
        search={{ value: searchQuery, onChange: setSearchQuery, placeholder: "Search events…" }}
      />

      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">

      {/* Filtered-empty state */}
      {!filtered.length && (
        <div className="text-center py-12 text-muted text-sm">No events match your filter.</div>
      )}

      {/* Timeline */}
      <div className="relative">
        {groups.map((group, gi) => (
            <div key={group.key}>
              {/* Month header */}
              <div className="flex items-center h-9" style={{ paddingTop: gi > 0 ? 8 : 0 }}>
                <div className="w-9 flex justify-center">
                  <div className="w-0.5 h-full bg-border-subtle" />
                </div>
                <span className="text-xs font-semibold uppercase tracking-widest text-muted ml-2">
                  {group.label}
                </span>
              </div>

              {group.events.map((ev, ei) => {
                const isLast = gi === groups.length - 1 && ei === group.events.length - 1;
                const showToday = todayPosition?.group === gi && todayPosition?.event === ei;

                return (
                  <div key={`${str(ev, "category")}-${ei}-${str(ev, "date")}`}>
                    {showToday && <TodayMarker />}
                    <EventCard event={ev} isLast={isLast} />
                  </div>
                );
              })}

              {gi === groups.length - 1 && !todayPosition && <TodayMarker />}
            </div>
          ))}
      </div>
    </div>
    </div>
  );
}

function TodayMarker() {
  return (
    <div className="flex items-center gap-2">
      <div className="w-9 flex justify-center relative">
        <div className="w-0.5 h-8 bg-border-subtle" />
        <div className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-red-500" />
      </div>
      <span className="text-[11px] font-bold text-white bg-red-500 px-2.5 py-0.5 rounded-full">
        Today
      </span>
      <div className="flex-1 border-t border-border-subtle" />
    </div>
  );
}

function EventCard({ event, isLast }: { event: Entity; isLast: boolean }) {
  const cat = str(event, "category");
  const color = dotColor(event);
  const catColor = CATEGORY_COLORS[cat] || "#0A84FF";
  const isFuture = bool(event, "is_future");
  const CatIcon = CATEGORIES.find((c) => c.id === cat)?.icon || FileText;
  const catLabel = CATEGORIES.find((c) => c.id === cat)?.label || cat;

  return (
    <div className="flex" style={{ opacity: isFuture ? 0.5 : 1 }}>
      {/* Spine */}
      <div className="w-9 flex flex-col items-center shrink-0">
        <div className="w-0.5 h-3.5 bg-border-subtle" />
        <div className="relative flex items-center justify-center">
          <div className="w-[18px] h-[18px] rounded-full" style={{ backgroundColor: color + "26" }} />
          <div className="absolute w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
        </div>
        {!isLast && <div className="w-0.5 flex-1 min-h-[46px] bg-border-subtle" />}
      </div>

      {/* Card */}
      <div className="flex-1 ml-2 mb-1">
        <div className="rounded-lg bg-surface-overlay p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <CatIcon size={14} style={{ color }} />
              <span className="text-sm font-semibold">{str(event, "title")}</span>
            </div>
            <span className="text-[11px] text-muted whitespace-nowrap shrink-0">
              {formatDate(str(event, "date"))}
            </span>
          </div>
          {str(event, "description") && (
            <p className="text-xs text-secondary mt-1">{str(event, "description")}</p>
          )}
          <span
            className="inline-block mt-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full"
            style={{ color: catColor, backgroundColor: catColor + "1F" }}
          >
            {catLabel}
          </span>
        </div>
      </div>
    </div>
  );
}
