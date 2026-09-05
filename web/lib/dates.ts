export function isoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function defaultDateRange(windowDays = 90): { dateFrom: string; dateTo: string } {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - windowDays);
  return { dateFrom: isoDate(start), dateTo: isoDate(end) };
}

/** "7 Jun – 5 Sep 2026" style range for captions. */
export function formatRange(from: string, to: string): string {
  const f = new Date(`${from}T00:00:00`);
  const t = new Date(`${to}T00:00:00`);
  if (Number.isNaN(f.getTime()) || Number.isNaN(t.getTime())) return `${from} – ${to}`;
  const day = (d: Date) => d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  const dayYear = (d: Date) => d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  return f.getFullYear() === t.getFullYear() ? `${day(f)} – ${dayYear(t)}` : `${dayYear(f)} – ${dayYear(t)}`;
}

/** "5 Sep 2026, 14:32" for saved-at stamps. */
export function formatStamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function datesAreValid(from: string, to: string): boolean {
  if (!from || !to) return false;
  return from < to;
}

export function laterLaunch(
  a: { display_name: string; launch_date_ae: string | null } | undefined,
  b: { display_name: string; launch_date_ae: string | null } | undefined,
): { name: string; date: string } | null {
  if (!a?.launch_date_ae || !b?.launch_date_ae) return null;
  return a.launch_date_ae >= b.launch_date_ae
    ? { name: a.display_name, date: a.launch_date_ae.slice(0, 10) }
    : { name: b.display_name, date: b.launch_date_ae.slice(0, 10) };
}
