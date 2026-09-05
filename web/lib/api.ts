const API_BASE = "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function errorMessage(text: string, status: number): string {
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
    if (parsed.detail != null) return JSON.stringify(parsed.detail);
  } catch {
    /* not JSON */
  }
  return text || `Request failed: ${status}`;
}

export async function apiSend<T>(path: string, method: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(errorMessage(text, res.status));
  }
  return res.json() as Promise<T>;
}

export type Company = {
  id: number;
  slug: string;
  display_name: string;
  appstore_id: string | null;
  play_package: string | null;
  launch_date_ae: string | null;
  is_super_app: boolean;
  aliases: string[];
  notes: string | null;
  hidden: boolean;
};

export type SavedComparison = {
  id: number;
  a: string;
  b: string;
  a_name: string;
  b_name: string;
  date_from: string;
  date_to: string;
  title: string | null;
  pinned: boolean;
  n_a: number;
  n_b: number;
  sample: { n_a: number; n_b: number; usable_a: number; usable_b: number; used: boolean } | null;
  headline: string | null;
  has_summary: boolean;
  data_as_of: string | null;
  created_at: string;
  last_viewed_at: string;
};

export type SavedComparisonFull = SavedComparison & {
  filters: Record<string, unknown>;
  snapshot: {
    compare: Record<string, any>;
    summary: Record<string, any> | null;
    journey?: Record<string, any>;
    kano?: Record<string, any>;
    ipa?: Record<string, any>;
  };
};

export type MetricDef = {
  label: string;
  meaning: string;
  formula: string;
};
