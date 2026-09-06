"use client";

import { GapChip } from "@/components/CompareCard";
import { MetricLabel } from "@/components/MetricLabel";
import { Card } from "@/components/ui";
import { describeDelta } from "@/lib/delta";
import type { MetricDef } from "@/lib/api";
import type { ReactNode } from "react";

export type KpiScoreCell = {
  value: string;
  note?: string;
};

export type KpiScoreRow = {
  metricKey: string;
  a: KpiScoreCell;
  b: KpiScoreCell;
  delta: number | null;
  unit: string;
  lowerIsBetter?: boolean;
  onClick?: () => void;
};

const VALUES = "grid w-full grid-cols-2 gap-6 md:w-[26rem] md:grid-cols-[8rem_8rem_6.5rem] md:gap-4";

export function KpiScoreboard({
  nameA,
  nameB,
  glossary,
  n,
  rows,
  notice,
}: {
  nameA: string;
  nameB: string;
  glossary: Record<string, MetricDef>;
  n?: number;
  rows: KpiScoreRow[];
  notice?: ReactNode;
}) {
  return (
    <Card className="overflow-hidden p-0">
      {notice ? <div className="border-b border-divider bg-wash px-6 py-2.5 text-caption text-fg-2">{notice}</div> : null}
      <div className="hidden items-center justify-between gap-6 border-b border-divider px-6 py-2.5 md:flex">
        <p className="text-caption text-fg-3">Metric</p>
        <div className={VALUES}>
          <p className="flex items-center gap-1.5 text-caption font-medium text-a">
            <span className="inline-block h-2 w-2 rounded-pill bg-a" aria-hidden />
            {nameA}
          </p>
          <p className="flex items-center gap-1.5 text-caption font-medium text-b">
            <span className="inline-block h-2 w-2 rounded-pill bg-b" aria-hidden />
            {nameB}
          </p>
          <p className="text-right text-caption text-fg-3">Gap</p>
        </div>
      </div>
      <ul>
        {rows.map((row) => (
          <ScoreRow key={row.metricKey} row={row} nameA={nameA} nameB={nameB} glossary={glossary} n={n} />
        ))}
      </ul>
    </Card>
  );
}

function ScoreRow({
  row,
  nameA,
  nameB,
  glossary,
  n,
}: {
  row: KpiScoreRow;
  nameA: string;
  nameB: string;
  glossary: Record<string, MetricDef>;
  n?: number;
}) {
  const spoken = describeDelta(row.delta, row.unit, nameA, nameB, row.lowerIsBetter);
  const label = `${spoken.text}${spoken.vs ? ` ${spoken.vs}` : ""}`;

  return (
    <li className="border-b border-divider last:border-b-0">
      <div
        className={`flex flex-col gap-3 px-6 py-4 md:flex-row md:items-center md:justify-between md:gap-6 ${row.onClick ? "cursor-pointer hover:bg-canvas" : ""}`}
        onClick={row.onClick}
        onKeyDown={
          row.onClick
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  row.onClick?.();
                }
              }
            : undefined
        }
        role={row.onClick ? "button" : undefined}
        tabIndex={row.onClick ? 0 : undefined}
        aria-label={row.onClick ? `${label}. Open matching reviews` : label}
      >
        <div className="flex items-start justify-between gap-3">
          <MetricLabel metricKey={row.metricKey} glossary={glossary} n={n} compact />
          <span className="md:hidden">
            <GapChip delta={row.delta} unit={row.unit} lowerIsBetter={row.lowerIsBetter} />
          </span>
        </div>
        <div className={VALUES}>
          <ScoreCell cell={row.a} name={nameA} tone="a" />
          <ScoreCell cell={row.b} name={nameB} tone="b" />
          <p className="hidden self-center text-right md:block">
            <GapChip delta={row.delta} unit={row.unit} lowerIsBetter={row.lowerIsBetter} />
          </p>
        </div>
      </div>
    </li>
  );
}

function ScoreCell({ cell, name, tone }: { cell: KpiScoreCell; name: string; tone: "a" | "b" }) {
  return (
    <div>
      <p className={`mb-0.5 text-caption font-medium md:hidden ${tone === "a" ? "text-a" : "text-b"}`}>{name}</p>
      <p className="text-section text-fg">{cell.value}</p>
      {cell.note ? <p className="text-caption text-fg-3">{cell.note}</p> : null}
    </div>
  );
}
