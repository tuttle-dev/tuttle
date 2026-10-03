export function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function formatHours(hours: number): string {
  const totalMinutes = Math.round(hours * 60);
  if (totalMinutes < 60) return `${totalMinutes}m`;
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

/** Minutes in "1h 30m", "1h30", "1:30", "90m", "1.5" or "1,5" (a bare number is hours); null if unreadable. */
export function parseDuration(text: string): number | null {
  const s = text.trim().toLowerCase().replace(",", ".");
  let m: RegExpMatchArray | null;
  let minutes: number;
  if ((m = s.match(/^(\d+(?:\.\d+)?)\s*h?$/))) minutes = parseFloat(m[1]) * 60;
  else if ((m = s.match(/^(\d+):([0-5]\d)$/))) minutes = +m[1] * 60 + +m[2];
  else if ((m = s.match(/^(\d+)\s*h\s*(\d+)\s*(?:m|min)?$/))) minutes = +m[1] * 60 + +m[2];
  else if ((m = s.match(/^(\d+)\s*(?:m|min)$/))) minutes = +m[1];
  else return null;
  return Math.round(minutes);
}
