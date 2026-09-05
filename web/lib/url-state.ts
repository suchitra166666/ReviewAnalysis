import { defaultDateRange } from "./dates";

export type DashState = {
  a: string;
  b: string;
  dateFrom: string;
  dateTo: string;
};

export function defaultState(): DashState {
  const range = defaultDateRange();
  return { a: "", b: "", dateFrom: range.dateFrom, dateTo: range.dateTo };
}

export function parseState(search: string): DashState {
  const q = new URLSearchParams(search);
  const range = defaultDateRange();
  return {
    a: q.get("a") ?? "",
    b: q.get("b") ?? "",
    dateFrom: q.get("from") ?? range.dateFrom,
    dateTo: q.get("to") ?? range.dateTo,
  };
}

export function serializeState(state: DashState): string {
  const q = new URLSearchParams();
  if (state.a) q.set("a", state.a);
  if (state.b) q.set("b", state.b);
  if (state.dateFrom) q.set("from", state.dateFrom);
  if (state.dateTo) q.set("to", state.dateTo);
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** API still accepts weighted / exclude_flagged; the UI always sends true. */
export function compareQuery(state: DashState): string {
  const q = new URLSearchParams();
  q.set("a", state.a);
  q.set("b", state.b);
  if (state.dateFrom) q.set("date_from", state.dateFrom);
  if (state.dateTo) q.set("date_to", state.dateTo);
  q.set("exclude_flagged", "true");
  q.set("weighted", "true");
  q.set("food_related_only", "true");
  return q.toString();
}
