import type { SavedComparison } from "./api";

export function savedTitle(row: Pick<SavedComparison, "title" | "a_name" | "b_name">): string {
  return row.title?.trim() || `${row.a_name} vs ${row.b_name}`;
}

/** Dashboard URL that recomputes this comparison from whatever data exists now. */
export function liveHref(row: Pick<SavedComparison, "a" | "b" | "date_from" | "date_to">): string {
  const q = new URLSearchParams({ a: row.a, b: row.b, from: row.date_from, to: row.date_to });
  return `/?${q.toString()}`;
}

/** Dashboard URL that shows the stored result exactly as it was. */
export function savedHref(id: number): string {
  return `/?saved=${id}`;
}

export function parseSavedId(search: string): number | null {
  const raw = new URLSearchParams(search).get("saved");
  if (!raw) return null;
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 ? n : null;
}
