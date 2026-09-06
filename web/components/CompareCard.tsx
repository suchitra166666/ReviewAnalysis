"use client";

import { Card } from "@/components/ui";
import { MetricLabel } from "@/components/MetricLabel";
import { describeDelta, formatDelta } from "@/lib/delta";
import type { MetricDef } from "@/lib/api";
import type { ReactNode } from "react";

export function CompareCard({
  title,
  metricKey,
  glossary,
  n,
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
  nameA: string;
  nameB: string;
  a: ReactNode;
  b: ReactNode;
  /** A minus B. Omit to hide the delta chip (e.g. distributions). */
  delta?: number | null;
  unit?: string;
  lowerIsBetter?: boolean;
  onClick?: () => void;
}) {
  const showDelta = delta !== undefined;
  const spoken = describeDelta(delta ?? null, unit ?? "", nameA, nameB, lowerIsBetter);

  return (
    <Card className={onClick ? "cursor-pointer" : undefined}>
      <div
        className="flex flex-col gap-4"
        onClick={onClick}
        onKeyDown={
          onClick
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onClick();
                }
              }
            : undefined
        }
        role={onClick ? "button" : undefined}
        tabIndex={onClick ? 0 : undefined}
        aria-label={onClick ? `${spoken.text}${spoken.vs ? ` ${spoken.vs}` : ""}. Open matching reviews` : undefined}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            {title ? <h3 className="text-card text-fg">{title}</h3> : null}
            <MetricLabel metricKey={metricKey} glossary={glossary} n={n} />
          </div>
          {showDelta ? <GapChip delta={delta ?? null} unit={unit ?? ""} lowerIsBetter={lowerIsBetter} /> : null}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-control bg-wash px-3 py-3">
            <p className="mb-1 text-caption font-medium text-a">{nameA}</p>
            {a}
          </div>
          <div className="rounded-control bg-wash px-3 py-3">
            <p className="mb-1 text-caption font-medium text-b">{nameB}</p>
            {b}
          </div>
        </div>
      </div>
    </Card>
  );
}

export function GapChip({
  delta,
  unit,
  lowerIsBetter,
}: {
  delta: number | null;
  unit: string;
  lowerIsBetter?: boolean;
}) {
  const chip = formatDelta(delta, unit, lowerIsBetter);
  const same = chip.arrow === "flat" && chip.text !== "—";
  return (
    <span className={`text-small font-medium tabular-nums ${chip.cls}`}>{same ? "Same" : chip.text}</span>
  );
}
