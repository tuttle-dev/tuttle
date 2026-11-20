import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { formatDate, localDateIso } from "../../api/entity";

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

/** A compact month calendar: clicking a day picks it. Days after *max* (YYYY-MM-DD)
 *  can't be picked. Weeks start on Monday, as in Time Tracking. */
export function MiniCalendar({ onPick, max, dayLabel = formatDate }: {
  onPick: (iso: string) => void; max?: string; dayLabel?: (iso: string) => string;
}) {
  const today = localDateIso();
  const [shown, setShown] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const year = shown.getFullYear();
  const month = shown.getMonth();
  const lead = (shown.getDay() + 6) % 7;
  const days = Array.from({ length: new Date(year, month + 1, 0).getDate() }, (_, i) => localDateIso(new Date(year, month, i + 1)));
  const lastShown = max !== undefined && localDateIso(new Date(year, month + 1, 1)) > max;
  const step = (by: number) => setShown(new Date(year, month + by, 1));
  const navButton = "p-1 rounded-md text-tertiary hover:text-primary hover:bg-bg-hover transition-colors disabled:opacity-30 disabled:pointer-events-none";

  return (
    <div className="w-[203px] select-none">
      <div className="flex items-center justify-between pl-1.5 pb-1">
        <span className="text-xs font-semibold text-primary">
          {shown.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
        </span>
        <div className="flex">
          <button type="button" onClick={() => step(-1)} aria-label="Previous month" className={navButton}><ChevronLeft size={14} /></button>
          <button type="button" onClick={() => step(1)} disabled={lastShown} aria-label="Next month" className={navButton}><ChevronRight size={14} /></button>
        </div>
      </div>
      <div className="grid grid-cols-7 gap-y-0.5 text-center">
        {WEEKDAYS.map((w) => <span key={w} className="h-6 text-[10px] font-medium leading-6 text-muted">{w}</span>)}
        {lead > 0 && <span style={{ gridColumn: `span ${lead}` }} />}
        {days.map((iso, i) => {
          const disabled = max !== undefined && iso > max;
          const isToday = iso === today;
          const weekend = (lead + i) % 7 >= 5;
          const tone = disabled ? "text-muted/35"
            : isToday ? "font-semibold text-status-success ring-1 ring-inset ring-status-success/60"
            : weekend ? "text-tertiary" : "text-secondary";
          return (
            <button key={iso} type="button" disabled={disabled} onClick={() => onPick(iso)}
              title={disabled ? undefined : dayLabel(iso)} aria-label={dayLabel(iso)} aria-current={isToday ? "date" : undefined}
              className={`mx-auto h-7 w-7 rounded-full text-xs tabular-nums transition-colors enabled:hover:bg-status-success enabled:hover:text-on-fill focus-visible:outline-2 focus-visible:outline-accent ${tone}`}>
              {i + 1}
            </button>
          );
        })}
        {/* Always six week rows, so the height doesn't jump between months. */}
        {Array.from({ length: 42 - lead - days.length }, (_, i) => <span key={`pad-${i}`} className="h-7" />)}
      </div>
    </div>
  );
}
