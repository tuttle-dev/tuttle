import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { rpc } from "../../api/rpc";
import { useStatusBar } from "../shared/status-bar-context";
import { formatHours } from "./format";

export type TimerStatus = "idle" | "running" | "pending";

export type TimerState = {
  status: TimerStatus;
  startTime: string | null;
  stoppedAt: string | null;
  elapsed: number;
  tag: string;
  title: string;
};

export type StopOutcome = { saved: boolean; durationHours: number; tag: string };

export type TimerControls = {
  state: TimerState;
  entryVersion: number;
  start: () => Promise<boolean>;
  stop: () => Promise<StopOutcome>;
  save: () => Promise<StopOutcome>;
  resume: () => void;
  discard: () => Promise<void>;
  update: (patch: { tag?: string; title?: string }, persist?: boolean) => void;
};

const IDLE: TimerState = { status: "idle", startTime: null, stoppedAt: null, elapsed: 0, tag: "", title: "" };

const TimerContext = createContext<TimerControls | null>(null);

export function useTimer(): TimerControls {
  const ctx = useContext(TimerContext);
  if (!ctx) throw new Error("useTimer must be used within TimerProvider");
  return ctx;
}

function elapsedSince(startIso: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(startIso).getTime()) / 1000));
}

export function TimerProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TimerState>(IDLE);
  const [entryVersion, setEntryVersion] = useState(0);
  const stateRef = useRef(state);
  stateRef.current = state;
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { showMessage } = useStatusBar();

  const stopTicking = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startTicking = useCallback((startIso: string) => {
    stopTicking();
    intervalRef.current = setInterval(() => {
      setState((s) => (s.status === "running" ? { ...s, elapsed: elapsedSince(startIso) } : s));
    }, 1000);
  }, [stopTicking]);

  useEffect(() => {
    (async () => {
      const res = await rpc<{ running: boolean; start_time?: string; tag?: string; title?: string }>(
        "timetracking.get_timer_state",
      );
      if (res.ok && res.data?.running && res.data.start_time) {
        const startTime = res.data.start_time;
        setState({
          status: "running",
          startTime,
          stoppedAt: null,
          elapsed: elapsedSince(startTime),
          tag: res.data.tag || "",
          title: res.data.title || "",
        });
        startTicking(startTime);
      }
    })();
    return stopTicking;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const update = useCallback((patch: { tag?: string; title?: string }, persist = true) => {
    setState((s) => ({ ...s, ...patch }));
    if (persist && stateRef.current.status !== "idle") {
      rpc("timetracking.update_timer", patch);
    }
  }, []);

  const start = useCallback(async (): Promise<boolean> => {
    const { tag, title } = stateRef.current;
    const res = await rpc<{ started: boolean; start_time: string }>("timetracking.start_timer", {
      tag: tag || null,
      title: title || null,
    });
    if (!res.ok || !res.data?.started) {
      showMessage(res.error || "The timer could not be started.", { type: "error" });
      return false;
    }
    const startTime = res.data.start_time;
    setState((s) => ({ ...s, status: "running", startTime, stoppedAt: null, elapsed: 0 }));
    startTicking(startTime);
    return true;
  }, [startTicking, showMessage]);

  const finish = useCallback(async (endTime: string | null): Promise<StopOutcome> => {
    const { tag, title } = stateRef.current;
    const res = await rpc<{ stopped: boolean; duration_hours: number }>("timetracking.stop_timer", {
      tag,
      title,
      end_time: endTime,
    });
    if (!res.ok || !res.data?.stopped) {
      showMessage(res.error || "The entry could not be saved.", { type: "error" });
      return { saved: false, durationHours: 0, tag };
    }
    stopTicking();
    setState((s) => ({ ...IDLE, tag: s.tag }));
    setEntryVersion((v) => v + 1);
    showMessage(`Tracked ${formatHours(res.data.duration_hours)} on ${tag}`, { type: "success" });
    return { saved: true, durationHours: res.data.duration_hours, tag };
  }, [stopTicking, showMessage]);

  const stop = useCallback(async (): Promise<StopOutcome> => {
    const s = stateRef.current;
    if (s.status !== "running") return { saved: false, durationHours: 0, tag: s.tag };
    if (!s.tag) {
      // Keep the moment the user pressed stop; the entry is saved once a project is chosen.
      stopTicking();
      const stoppedAt = new Date().toISOString();
      setState((cur) => ({
        ...cur,
        status: "pending",
        stoppedAt,
        elapsed: cur.startTime ? elapsedSince(cur.startTime) : cur.elapsed,
      }));
      return { saved: false, durationHours: 0, tag: "" };
    }
    return finish(null);
  }, [finish, stopTicking]);

  const save = useCallback(async (): Promise<StopOutcome> => {
    const s = stateRef.current;
    if (!s.tag) {
      showMessage("Choose a project for this entry before saving it.", { type: "error" });
      return { saved: false, durationHours: 0, tag: "" };
    }
    return finish(s.stoppedAt);
  }, [finish, showMessage]);

  const resume = useCallback(() => {
    const s = stateRef.current;
    if (s.status !== "pending" || !s.startTime) return;
    setState((cur) => ({ ...cur, status: "running", stoppedAt: null }));
    startTicking(s.startTime);
  }, [startTicking]);

  const discard = useCallback(async () => {
    await rpc("timetracking.discard_timer");
    stopTicking();
    setState((s) => ({ ...IDLE, tag: s.tag }));
  }, [stopTicking]);

  return (
    <TimerContext.Provider value={{ state, entryVersion, start, stop, save, resume, discard, update }}>
      {children}
    </TimerContext.Provider>
  );
}
