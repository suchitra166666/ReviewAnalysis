"use client";

import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card } from "@/components/ui";
import { MetricLabel } from "@/components/MetricLabel";
import { describeDelta } from "@/lib/delta";
import type { MetricDef } from "@/lib/api";
import type { ReactNode } from "react";

export function CompareCard({
  title,
  metricKey,
  glossary,
  n,
  low,
  nameA,
  nameB,
  a,
  b,
  delta,
  unit,
  lowerIsBetter,
  onClick,
}: {
  title?: string;
  metricKey: string;
  glossary: Record<string, MetricDef>;
  n?: number;
  low?: boolean;
  /** Company names shown above each value so the two sides never rely on colour alone. */
  nameA: string;
  nameB: string;
  a: ReactNode;
  b: ReactNode;
  /** A minus B. Omit to hide the middle column (e.g. distributions). */
  delta?: number | null;
  unit?: string;
  lowerIsBetter?: boolean;
  onClick?: () => void;
}) {
  const showDelta = delta !== undefined;
  const d = describeDelta(delta ?? null, unit ?? "", nameA, nameB, lowerIsBetter);
  return (
    <Card low={low} className={onClick ? "cursor-pointer" : undefined}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          {title ? <h3 className="text-card text-fg">{title}</h3> : null}
          <MetricLabel metricKey={metricKey} glossary={glossary} n={n} />
        </div>
        {low ? <p className="text-caption text-fg-3">Low confidence — {n ?? 0} reviews</p> : null}
      </div>
      <div className={`grid grid-cols-1 gap-4 ${showDelta ? "md:grid-cols-[1fr_128px_1fr]" : "md:grid-cols-2"} md:items-start`}>
        <div className="border-l-[3px] border-a pl-3">
          <p className="mb-1 text-caption font-medium text-a">{nameA}</p>
          {a}
        </div>
        {showDelta ? (
          <button
            type="button"
            onClick={onClick}
            className="flex flex-col items-center justify-center self-center text-center"
            aria-label={`${d.text}${d.vs ? ` ${d.vs}` : ""}. Open matching reviews`}
          >
            <span className={`inline-flex items-start gap-1 text-small ${d.cls}`}>
              {d.arrow === "up" ? <ArrowUpRight size={16} strokeWidth={1.5} className="mt-0.5 shrink-0" /> : null}
              {d.arrow === "down" ? <ArrowDownRight size={16} strokeWidth={1.5} className="mt-0.5 shrink-0" /> : null}
              <span>{d.text}</span>
            </span>
            {d.vs ? <span className="text-caption text-fg-3">{d.vs}</span> : null}
          </button>
        ) : null}
        <div className="border-l-[3px] border-b pl-3">
          <p className="mb-1 text-caption font-medium text-b">{nameB}</p>
          {b}
        </div>
      </div>
    </Card>
  );
}
