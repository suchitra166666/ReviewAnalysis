"use client";

import { Info } from "lucide-react";
import type { MetricDef } from "@/lib/api";

export function MetricLabel({
  metricKey,
  glossary,
  n,
  className = "",
}: {
  metricKey: string;
  glossary: Record<string, MetricDef>;
  n?: number;
  className?: string;
}) {
  const def = glossary[metricKey];
  const label = def?.label ?? metricKey.replace(/_/g, " ");
  return (
    <span className={`inline-flex items-center gap-1 text-small text-fg-3 ${className}`}>
      <span>{label}</span>
      <span className="relative group inline-flex">
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center text-fg-3"
          aria-label={`About ${label}`}
        >
          <Info size={16} strokeWidth={1.5} />
        </button>
        <span className="pointer-events-none absolute left-0 top-full z-20 hidden w-72 rounded-control border border-border bg-bg p-3 text-left text-caption text-fg shadow-none group-hover:block group-focus-within:block">
          <span className="block text-small text-fg">{def?.meaning ?? "No glossary entry yet."}</span>
          <span className="mt-2 block text-fg-2">Formula: {def?.formula ?? "—"}</span>
          {n !== undefined && <span className="mt-1 block text-fg-3">n = {n.toLocaleString()}</span>}
        </span>
      </span>
    </span>
  );
}
