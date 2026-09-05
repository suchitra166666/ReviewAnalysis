export type BetterSide = "a" | "b" | null;

export function deltaColor(better: BetterSide, side: "a" | "b" | "delta"): string {
  if (side === "delta") {
    if (!better) return "text-muted";
    return "text-good";
  }
  return side === "a" ? "text-a" : "text-b";
}

/** Shares and point differences arrive as fractions (0.184); show them as points. */
function magnitude(value: number, unit: string): string {
  const v = Math.abs(value);
  if (unit === "%" || unit === "pts") return `${(v * 100).toFixed(1)} pts`;
  if (unit === "★") return `${v.toFixed(1)}★`;
  if (unit === "" || unit === "n") return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(1);
  return `${v.toFixed(1)} ${unit}`.trim();
}

export function formatDelta(
  value: number | null | undefined,
  unit: string,
  lowerIsBetter = false,
): { text: string; cls: string; arrow: "up" | "down" | "flat" } {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return { text: "—", cls: "text-muted", arrow: "flat" };
  }
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  const good = lowerIsBetter ? value < 0 : value > 0;
  const bad = lowerIsBetter ? value > 0 : value < 0;
  return {
    text: `${sign}${magnitude(value, unit)}`,
    cls: good ? "text-good" : bad ? "text-bad" : "text-muted",
    arrow: value > 0 ? "up" : value < 0 ? "down" : "flat",
  };
}

/**
 * Plain-language reading of A minus B, e.g. "Careem is 43 lower".
 * Colour is judged from A's point of view: green when A is better off.
 */
export function describeDelta(
  value: number | null | undefined,
  unit: string,
  nameA: string,
  nameB: string,
  lowerIsBetter = false,
): { text: string; cls: string; arrow: "up" | "down" | "flat"; vs: string } {
  const vs = `than ${nameB}`;
  if (value === null || value === undefined || Number.isNaN(value)) {
    return { text: "Not comparable", cls: "text-muted", arrow: "flat", vs: "" };
  }
  if (Math.abs(value) < 1e-9) {
    return { text: "Same for both", cls: "text-muted", arrow: "flat", vs: "" };
  }
  const base = formatDelta(value, unit, lowerIsBetter);
  const direction = value > 0 ? "higher" : "lower";
  return { text: `${nameA} is ${magnitude(value, unit)} ${direction}`, cls: base.cls, arrow: base.arrow, vs };
}

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatStars(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(1)}★`;
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString();
}

export function maskKey(last4: string | null | undefined): string {
  if (!last4) return "No key";
  return `••••${last4}`;
}
