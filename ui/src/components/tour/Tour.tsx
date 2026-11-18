import { createContext, useCallback, useContext, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Plus, X } from "lucide-react";
import { rpc } from "../../api/rpc";
import { localDateIso } from "../../api/entity";
import type { Entity } from "../../api/types";
import { useNavigation } from "../shared/NavigationContext";
import { TOUR_PARTS, TOUR_PROJECT_TAG, TOUR_STEPS, type Side, type TourRecords, type TourStep, type TourTarget } from "./steps";

/** sessionStorage key: a tour to start once the window has reloaded into the demo. */
export const TOUR_PENDING_KEY = "tuttle-tour-pending";

const TourContext = createContext<{ start: () => void }>({ start: () => {} });

/** Starts the tour, switching to the demo data first if needed. */
export function useTour() {
  return useContext(TourContext);
}

type Props = {
  children: ReactNode;
  /** The tour runs on the demo data. */
  inDemo: boolean;
  /** The user's own database, to return to after the tour. */
  ownDbFile: string | null;
  /** Switch to the demo; the window reloads and the tour starts there. */
  onStartInDemo: () => void;
  onSwitchUser: (dbFile: string) => void;
  /** Open the setup of the user's own business. */
  onSetUp: () => void;
  /** Start as soon as the demo is active. */
  pending: boolean;
  onPendingTaken: () => void;
};

export function TourProvider({ children, inDemo, ownDbFile, onStartInDemo, onSwitchUser, onSetUp, pending, onPendingTaken }: Props) {
  const { navigate } = useNavigation();
  const [run, setRun] = useState<{ index: number; records: TourRecords } | null>(null);
  const starting = useRef(false);

  const begin = useCallback(async () => {
    if (starting.current) return;
    starting.current = true;
    const records = await findRecords();
    starting.current = false;
    setRun({ index: 0, records });
  }, []);

  useEffect(() => {
    if (!pending || !inDemo) return;
    onPendingTaken();
    begin();
  }, [pending, inDemo, onPendingTaken, begin]);

  const start = useCallback(() => {
    if (run) return;
    if (inDemo) begin();
    else onStartInDemo();
  }, [run, inDemo, begin, onStartInDemo]);

  function end() {
    setRun(null);
    navigate("dashboard");
  }

  return (
    <TourContext.Provider value={{ start }}>
      {children}
      {run && (
        <TourOverlay
          index={run.index}
          records={run.records}
          onIndex={(index) => setRun((r) => r && { ...r, index })}
          onEnd={end}
          finish={ownDbFile
            ? { label: "Back to my business", action: () => { setRun(null); onSwitchUser(ownDbFile); } }
            : { label: "Set up my business", action: () => { end(); onSetUp(); } }}
        />
      )}
    </TourContext.Provider>
  );
}

// -- Finding the demo records ---------------------------------------------------

type CalendarEvent = { date: string; is_future: boolean; entry_id: number | null };

async function findRecords(): Promise<TourRecords> {
  const res = await rpc<Entity[]>("projects.get_all");
  const project = res.ok ? res.data?.find((p) => p.tag === TOUR_PROJECT_TAG) : undefined;
  if (!project) return {};
  const contract = project.contract as Entity | undefined;
  const client = contract?.client as Entity | undefined;
  return { projectId: project.id, contractId: contract?.id, clientId: client?.id, day: await recentDay(TOUR_PROJECT_TAG) };
}

/** The latest past day with time on the project: best with time from both the calendar and Tuttle. */
async function recentDay(tag: string): Promise<string | undefined> {
  const now = new Date();
  const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const events: CalendarEvent[] = [];
  for (const d of [now, lastMonth]) {
    const res = await rpc<{ events: CalendarEvent[] }>("timetracking.get_calendar_data",
      { year: d.getFullYear(), month: d.getMonth() + 1, project_tag: tag });
    if (res.ok && res.data) events.push(...res.data.events);
  }
  const today = localDateIso(now);
  const days = new Map<string, number>();
  for (const ev of events) {
    if (ev.is_future || ev.date > today) continue;
    days.set(ev.date, (days.get(ev.date) ?? 0) | (ev.entry_id != null ? 2 : 1));
  }
  return [...days].sort(([a, sa], [b, sb]) => sb - sa || b.localeCompare(a))[0]?.[0];
}

// -- The overlay ------------------------------------------------------------------

type Rect = { x: number; y: number; w: number; h: number };

/** Space around a highlight, its corner radius, and the time the tour points at the way there. */
const PAD = 6;
const RADIUS = 10;
const VIA_MS = 450;
const MARGIN = 8;
/** Highlights drawn at once; the rest of the pool stays collapsed so moves can animate. */
const POOL = 4;

function visibleRects(selector: string): Rect[] {
  return [...document.querySelectorAll(selector)]
    .map((el) => el.getBoundingClientRect())
    .filter((r) => r.width > 0 && r.height > 0)
    .map((r) => ({ x: r.left, y: r.top, w: r.width, h: r.height }));
}

function union(rs: Rect[]): Rect {
  const x = Math.min(...rs.map((r) => r.x)), y = Math.min(...rs.map((r) => r.y));
  return { x, y, w: Math.max(...rs.map((r) => r.x + r.w)) - x, h: Math.max(...rs.map((r) => r.y + r.h)) - y };
}

function measure(targets: TourTarget[] = []): (Rect | null)[] {
  return targets.map((t) => {
    const rs = visibleRects(t.selector);
    return rs.length === 0 ? null : t.each ? rs : [union(rs)];
  }).flatMap((rs) => rs ?? [null]);
}

const padded = (r: Rect): Rect => ({ x: r.x - PAD, y: r.y - PAD, w: r.w + 2 * PAD, h: r.h + 2 * PAD });
const overlaps = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const same = (a: Rect[], b: Rect[]) => a.length === b.length && a.every((r, i) =>
  Math.abs(r.x - b[i].x) < 0.5 && Math.abs(r.y - b[i].y) < 0.5 && Math.abs(r.w - b[i].w) < 0.5 && Math.abs(r.h - b[i].h) < 0.5);

/** Where the card goes: beside its anchor, clear of every highlight, inside the window. */
function placeCard(card: { w: number; h: number }, anchor: Rect | null, holes: Rect[], sides: Side[]) {
  const vw = window.innerWidth, vh = window.innerHeight;
  const clampX = (x: number) => Math.max(MARGIN, Math.min(x, vw - card.w - MARGIN));
  const clampY = (y: number) => Math.max(MARGIN, Math.min(y, vh - card.h - MARGIN));
  if (!anchor) return { x: (vw - card.w) / 2, y: (vh - card.h) / 2 };
  const gap = 16;
  const at: Record<Side, { x: number; y: number }> = {
    left: { x: anchor.x - gap - card.w, y: clampY(anchor.y) },
    right: { x: anchor.x + anchor.w + gap, y: clampY(anchor.y) },
    above: { x: clampX(anchor.x + (anchor.w - card.w) / 2), y: anchor.y - gap - card.h },
    below: { x: clampX(anchor.x + (anchor.w - card.w) / 2), y: anchor.y + anchor.h + gap },
  };
  const corners = [
    { x: vw - card.w - MARGIN, y: vh - card.h - 40 },
    { x: vw - card.w - MARGIN, y: 64 },
  ];
  const inside = (p: { x: number; y: number }) =>
    p.x >= MARGIN && p.y >= MARGIN && p.x + card.w <= vw - MARGIN && p.y + card.h <= vh - MARGIN;
  // How much of the highlights the card would cover.
  const covered = (p: { x: number; y: number }) => holes.reduce((sum, h) => {
    const w = Math.min(p.x + card.w, h.x + h.w) - Math.max(p.x, h.x);
    const hh = Math.min(p.y + card.h, h.y + h.h) - Math.max(p.y, h.y);
    return sum + (w > 0 && hh > 0 ? w * hh : 0);
  }, 0);
  const candidates = [...sides.map((s) => at[s]), ...corners].filter(inside);
  return candidates.find((p) => covered(p) === 0)
    ?? candidates.sort((a, b) => covered(a) - covered(b))[0]
    ?? corners[0];
}

function TourOverlay({ index, records, onIndex, onEnd, finish }: {
  index: number;
  records: TourRecords;
  onIndex: (index: number) => void;
  onEnd: () => void;
  finish: { label: string; action: () => void };
}) {
  const { navigate } = useNavigation();
  const step = TOUR_STEPS[index];
  const [phase, setPhase] = useState<"via" | "wait" | "show">("wait");
  const [via, setVia] = useState<string | null>(null);
  const [holes, setHoles] = useState<Rect[]>([]);
  const [pulses, setPulses] = useState<Rect[]>([]);
  const [anchor, setAnchor] = useState<Rect | null>(null);
  const [cardPos, setCardPos] = useState<{ x: number; y: number } | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const primaryRef = useRef<HTMLButtonElement>(null);
  const previous = useRef<TourStep | null>(null);
  const maskId = `tour-mask-${useId().replace(/[^\w-]/g, "")}`;
  const titleId = useId();

  // A new step: point at the way there, go there, wait for what it shows.
  useEffect(() => {
    let cancelled = false;
    const prev = previous.current;
    previous.current = step;
    (async () => {
      const way = prev && prev.view !== step.view ? `[data-nav="${step.view}"]` : prev && step.via ? step.via : null;
      if (way) {
        setVia(way);
        setPhase("via");
        await new Promise((r) => setTimeout(r, VIA_MS));
        if (cancelled) return;
      }
      setPhase("wait");
      navigate(step.view, step.filter?.(records));
      const deadline = Date.now() + 2500;
      while (!cancelled && Date.now() < deadline && measure(step.targets).some((r) => r === null)) {
        await new Promise((r) => setTimeout(r, 60));
      }
      if (cancelled) return;
      // Bring the anchor into view, all of it if it fits: its last element, then its first.
      const anchorTarget = step.targets?.[step.anchor ?? 0];
      const els = anchorTarget ? [...document.querySelectorAll(anchorTarget.selector)] : [];
      els.at(-1)?.scrollIntoView({ block: "nearest" });
      els[0]?.scrollIntoView({ block: "nearest" });
      (document.activeElement as HTMLElement | null)?.blur?.();
      setPhase("show");
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per step
  }, [index]);

  // Follow the highlighted elements while they move (scrolling, resizing, loading).
  useEffect(() => {
    let frame = 0;
    const tick = () => {
      const found = phase === "via" && via ? [visibleRects(via)[0] ?? null] : phase === "show" ? measure(step.targets) : null;
      if (found) {
        const next = found.filter((r): r is Rect => r !== null).map(padded);
        setHoles((cur) => same(cur, next) ? cur : next);
        const anchorRect = phase === "show" ? found[step.anchor ?? 0] : null;
        const a = anchorRect ? padded(anchorRect) : null;
        setAnchor((cur) => (a && cur && same([cur], [a])) || (!a && !cur) ? cur : a);
        const p = phase === "show" ? (step.pulses ?? []).flatMap((s) => visibleRects(s).slice(0, 1)) : [];
        setPulses((cur) => same(cur, p) ? cur : p);
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [phase, via, step]);

  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!card || phase !== "show") return;
    setCardPos(placeCard({ w: card.offsetWidth, h: card.offsetHeight }, anchor, holes, step.sides ?? ["right", "left", "below", "above"]));
  }, [phase, anchor, holes, step]);

  useEffect(() => { if (phase === "show") primaryRef.current?.focus({ preventScroll: true }); }, [phase, index]);

  const outro = TOUR_STEPS.length - 1;
  const next = () => onIndex(Math.min(index + 1, outro));
  const back = () => onIndex(Math.max(index - 1, 0));
  const close = () => (step.kind ? onEnd() : onIndex(outro));

  // The tour has the keyboard: the app underneath must not react.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const handlers: Record<string, () => void> = { ArrowRight: next, ArrowLeft: back, Escape: close };
      const handler = handlers[e.key];
      if (handler) { e.preventDefault(); e.stopPropagation(); handler(); }
      else if (e.key !== "Tab" && e.key !== "Enter" && e.key !== " ") { e.stopPropagation(); }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  });

  const pool: Rect[] = Array.from({ length: POOL }, (_, i) => holes[i]
    ?? (holes[0] ? { x: holes[0].x + holes[0].w / 2, y: holes[0].y + holes[0].h / 2, w: 0, h: 0 } : { x: innerWidth / 2, y: innerHeight / 2, w: 0, h: 0 }));
  const geometry = (r: Rect) => ({ x: r.x, y: r.y, width: r.w, height: r.h, transition: "x .3s, y .3s, width .3s, height .3s" });
  const shown = phase === "show" && cardPos !== null;

  return createPortal(
    <div className="fixed inset-0 z-[70] select-none" onMouseDown={(e) => e.preventDefault()}>
      <svg className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden="true">
        <defs>
          <mask id={maskId}>
            <rect width="100%" height="100%" fill="white" />
            {pool.map((r, i) => <rect key={i} rx={RADIUS} fill="black" style={geometry(r)} />)}
          </mask>
        </defs>
        <rect width="100%" height="100%" fill="rgb(0 0 0 / 0.5)" mask={`url(#${maskId})`} />
        {pool.map((r, i) => (
          <rect key={i} rx={RADIUS} fill="none" stroke="var(--color-accent)" strokeWidth={2}
            opacity={r.w > 0 ? 0.8 : 0} style={geometry(r)} />
        ))}
      </svg>

      {pulses.map((r, i) => (
        <div key={i} className="tour-pulse fixed pointer-events-none"
          style={{ left: r.x - 3, top: r.y - 3, width: r.w + 6, height: r.h + 6 }} />
      ))}

      <div ref={cardRef} role="dialog" aria-modal="true" aria-labelledby={titleId}
        onMouseDown={(e) => e.stopPropagation()}
        className={`fixed w-[350px] rounded-xl border border-border-subtle bg-bg-content text-primary shadow-2xl px-[18px] pt-4 pb-3.5
          transition-[left,top,opacity] duration-300 ${shown ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        style={{ left: cardPos?.x ?? -9999, top: cardPos?.y ?? 0 }}>
        <button onClick={close} aria-label="End tour"
          className="absolute top-2.5 right-2.5 p-1 rounded-md text-muted hover:text-primary hover:bg-bg-hover transition-colors">
          <X size={14} />
        </button>
        {step.part !== undefined && (
          <Chain labels={TOUR_PARTS[step.part]} current={step.node ?? 0}
            onSelect={(node) => onIndex(TOUR_STEPS.findIndex((s) => s.part === step.part && s.node === node))} />
        )}
        <h3 id={titleId} className="text-[15px] font-semibold tracking-tight mb-1 pr-6">{step.title}</h3>
        <p className="text-[13px] leading-relaxed text-secondary">{withChips(step.body)}</p>
        <div className="flex justify-end gap-2 mt-3.5">
          {step.kind === "intro" ? (<>
            <CardButton onClick={onEnd}>Not now</CardButton>
            <CardButton primary buttonRef={primaryRef} onClick={next}>Start tour</CardButton>
          </>) : step.kind === "outro" ? (<>
            <CardButton onClick={onEnd}>Keep exploring</CardButton>
            <CardButton primary buttonRef={primaryRef} onClick={finish.action}>{finish.label}</CardButton>
          </>) : (<>
            <CardButton onClick={back}>Back</CardButton>
            <CardButton primary buttonRef={primaryRef} onClick={next}>{index === outro - 1 ? "Finish" : "Next"}</CardButton>
          </>)}
        </div>
      </div>
    </div>,
    document.body,
  );
}

/** The steps of one part: done, current, to come. */
function Chain({ labels, current, onSelect }: { labels: string[]; current: number; onSelect: (node: number) => void }) {
  const n = labels.length;
  return (
    <div className="relative grid mb-3.5 mr-6" style={{ gridTemplateColumns: `repeat(${n}, 1fr)` }}>
      <div className="absolute top-1 h-px bg-border-subtle" style={{ left: `${50 / n}%`, right: `${50 / n}%` }} />
      <div className="absolute top-1 h-px bg-accent/45 transition-[width] duration-300"
        style={{ left: `${50 / n}%`, width: `${(current / (n - 1)) * (100 - 100 / n)}%` }} />
      {labels.map((label, i) => (
        <button key={label} onClick={() => onSelect(i)} aria-current={i === current ? "step" : undefined}
          className="relative flex flex-col items-center gap-1.5 group">
          <span className={`w-[9px] h-[9px] rounded-full transition-all ${
            i === current ? "bg-accent scale-125" : i < current ? "bg-accent/45" : "bg-border-subtle"}`} />
          <span className={`text-[10.5px] whitespace-nowrap group-hover:text-primary ${
            i === current ? "text-primary font-semibold" : i < current ? "text-tertiary" : "text-muted"}`}>{label}</span>
        </button>
      ))}
    </div>
  );
}

function CardButton({ primary, onClick, buttonRef, children }: {
  primary?: boolean; onClick: () => void; buttonRef?: React.Ref<HTMLButtonElement>; children: ReactNode;
}) {
  return (
    <button ref={buttonRef} onClick={onClick}
      className={`px-3 py-1 rounded-md text-xs font-medium whitespace-nowrap transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 ${primary
        ? "bg-accent text-on-fill border border-accent hover:bg-accent/85"
        : "text-secondary border border-border-subtle hover:bg-bg-hover hover:border-border"}`}>
      {children}
    </button>
  );
}

/** The body text, with "{new}" drawn as the toolbar's New button. */
function withChips(body: string) {
  const [before, after] = body.split("{new}");
  if (after === undefined) return body;
  return (<>
    {before}
    <span className="inline-flex items-center gap-0.5 px-1.5 h-[19px] rounded-[5px] bg-accent text-on-fill text-[11.5px] font-medium align-[1px]">
      <Plus size={11} /> New
    </span>
    {after}
  </>);
}
