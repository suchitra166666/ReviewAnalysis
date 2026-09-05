"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  ReferenceDot,
  ReferenceLine,
  XAxis,
  YAxis,
  ZAxis,
  Legend,
  Line,
  LineChart,
  Tooltip,
} from "recharts";
import { ArabicText } from "@/components/ArabicText";
import { CompareCard } from "@/components/CompareCard";
import { MetricLabel } from "@/components/MetricLabel";
import { Sparkline } from "@/components/Sparkline";
import { Button, Card, Pill, Skeleton } from "@/components/ui";
import { apiGet, type MetricDef } from "@/lib/api";
import { formatCount, formatPct, formatStars } from "@/lib/delta";

type AnyRec = Record<string, any>;
type Glossary = Record<string, MetricDef>;

function SectionFrame({
  title,
  loading,
  empty,
  children,
}: {
  title: string;
  loading?: boolean;
  empty?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-4">
      <h2 className="text-section">{title}</h2>
      {loading ? <Skeleton className="h-40" /> : empty ? <Card><p className="text-body">{empty}</p></Card> : children}
    </section>
  );
}

function Kpi({ value }: { value: string }) {
  return <p className="text-kpi text-fg">{value}</p>;
}

function Ci({ ci }: { ci?: { low?: number; high?: number } | null }) {
  if (!ci || ci.low == null || ci.high == null) return null;
  const span = Math.abs((ci.high - ci.low) / 2);
  return <p className="text-caption text-fg-3">±{(span * 100).toFixed(1)}</p>;
}

export function SummarySection({
  summary,
  watch,
  loading,
  onTheme,
}: {
  summary?: AnyRec;
  watch: string[];
  loading?: boolean;
  onTheme: (t: string) => void;
}) {
  const text = summary?.executive_summary;
  const empty = !loading && !text && !watch.length;
  return (
    <SectionFrame title="Summary" loading={loading} empty={empty ? "Narrative will appear after a summarise run." : undefined}>
      {!empty || text || watch.length ? (
        <Card>
          <p className="text-body">{text || "Narrative will appear after a summarise run."}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {watch.map((t) => (
              <button key={t} type="button" onClick={() => onTheme(t)}>
                <Pill>{t.replace(/_/g, " ")}</Pill>
              </button>
            ))}
          </div>
        </Card>
      ) : null}
    </SectionFrame>
  );
}

/** Names the two sides once so no chart depends on colour alone. */
export function CompanyLegend({
  nameA,
  nameB,
  note,
  sides = true,
}: {
  nameA: string;
  nameB: string;
  note?: string;
  /** Mention left/right placement (side-by-side cards) or just the colours (charts). */
  sides?: boolean;
}) {
  return (
    <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-fg-3">
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-pill bg-a" aria-hidden />
        <span className="text-fg-2">{nameA}</span>
        {sides ? (
          <>
            <span className="hidden md:inline">left</span>
            <span className="md:hidden">top</span>
          </>
        ) : null}
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-2.5 rounded-pill bg-b" aria-hidden />
        <span className="text-fg-2">{nameB}</span>
        {sides ? (
          <>
            <span className="hidden md:inline">right</span>
            <span className="md:hidden">bottom</span>
          </>
        ) : null}
      </span>
      <span>{note ?? `Differences read as ${nameA} compared with ${nameB}.`}</span>
    </p>
  );
}

export function KpiSection({
  a,
  b,
  deltas,
  glossary,
  onExplore,
}: {
  a: AnyRec;
  b: AnyRec;
  deltas: AnyRec[];
  glossary: Glossary;
  onExplore: (extra: AnyRec) => void;
}) {
  const oa = a.overview;
  const ob = b.overview;
  const n = oa?.meta?.n_used ?? 0;
  const low = Boolean(oa?.meta?.low_confidence || ob?.meta?.low_confidence);
  const d = (key: string) => deltas.find((x) => x.key === key)?.delta ?? null;
  if (!oa || !ob) return <SectionFrame title="Key numbers" empty="Key numbers are not available for this range.">{null}</SectionFrame>;
  const nameA = oa.meta?.company_name ?? "A";
  const nameB = ob.meta?.company_name ?? "B";
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-section">Key numbers</h2>
        <CompanyLegend nameA={nameA} nameB={nameB} />
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <CompareCard
          metricKey="reviews_analysed"
          glossary={glossary}
          n={n}
          low={low}
          nameA={nameA}
          nameB={nameB}
          a={<Kpi value={formatCount(oa.reviews_analysed)} />}
          b={<Kpi value={formatCount(ob.reviews_analysed)} />}
          delta={d("reviews_analysed")}
          unit=""
          onClick={() => onExplore({})}
        />
        <CompareCard
          metricKey="analysed_average_rating"
          glossary={glossary}
          n={n}
          low={low}
          nameA={nameA}
          nameB={nameB}
          a={
            <div>
              <Kpi value={formatStars(oa.analysed_average_rating?.value)} />
              <p className="text-caption text-fg-2">
                Store says {formatStars(oa.store_headline_rating?.value)} · Reviews say {formatStars(oa.analysed_average_rating?.value)}
              </p>
              <Sparkline values={oa.sparkline_rating ?? []} color="var(--a)" />
            </div>
          }
          b={
            <div>
              <Kpi value={formatStars(ob.analysed_average_rating?.value)} />
              <p className="text-caption text-fg-2">
                Store says {formatStars(ob.store_headline_rating?.value)} · Reviews say {formatStars(ob.analysed_average_rating?.value)}
              </p>
              <Sparkline values={ob.sparkline_rating ?? []} color="var(--b)" />
            </div>
          }
          delta={d("analysed_average_rating")}
          unit="★"
          onClick={() => onExplore({})}
        />
        <CompareCard
          metricKey="positive_pct"
          glossary={glossary}
          n={n}
          low={low}
          nameA={nameA}
          nameB={nameB}
          a={
            <div>
              <Kpi value={formatPct(oa.positive_pct?.value)} />
              <Ci ci={oa.positive_pct?.ci} />
            </div>
          }
          b={
            <div>
              <Kpi value={formatPct(ob.positive_pct?.value)} />
              <Ci ci={ob.positive_pct?.ci} />
            </div>
          }
          delta={d("positive_pct")}
          unit="%"
          onClick={() => onExplore({ sentiment: "positive" })}
        />
        <CompareCard
          metricKey="negative_pct"
          glossary={glossary}
          n={n}
          low={low}
          nameA={nameA}
          nameB={nameB}
          a={
            <div>
              <Kpi value={formatPct(oa.negative_pct?.value)} />
              <Ci ci={oa.negative_pct?.ci} />
            </div>
          }
          b={
            <div>
              <Kpi value={formatPct(ob.negative_pct?.value)} />
              <Ci ci={ob.negative_pct?.ci} />
            </div>
          }
          delta={d("negative_pct")}
          unit="%"
          lowerIsBetter
          onClick={() => onExplore({ sentiment: "negative" })}
        />
        <CompareCard
          metricKey="net_sentiment"
          glossary={glossary}
          n={n}
          low={low}
          nameA={nameA}
          nameB={nameB}
          a={<Kpi value={formatPct(oa.net_sentiment?.value)} />}
          b={<Kpi value={formatPct(ob.net_sentiment?.value)} />}
          delta={d("net_sentiment")}
          unit="pts"
          onClick={() => onExplore({})}
        />
        <CompareCard
          metricKey="promo_dependence"
          glossary={glossary}
          n={n}
          low={low}
          nameA={nameA}
          nameB={nameB}
          a={<Kpi value={formatPct(oa.promo_dependence?.value)} />}
          b={<Kpi value={formatPct(ob.promo_dependence?.value)} />}
          delta={d("promo_dependence")}
          unit="%"
          lowerIsBetter
          onClick={() => onExplore({})}
        />
      </div>
    </section>
  );
}

export function StarsSection({ a, b, glossary }: { a: AnyRec; b: AnyRec; glossary: Glossary }) {
  const [raw, setRaw] = useState(false);
  const sa = a.star_scenario;
  const sb = b.star_scenario;
  if (!sa?.buckets?.length && !sb?.buckets?.length) {
    return <SectionFrame title="What the stars are telling you" empty="No star distribution for this range.">{null}</SectionFrame>;
  }
  const nameA = a.overview?.meta?.company_name ?? "A";
  const nameB = b.overview?.meta?.company_name ?? "B";
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-section">What the stars are telling you</h2>
          <CompanyLegend nameA={nameA} nameB={nameB} note="Share of analysed reviews at each star level." />
        </div>
        <button type="button" className="text-small text-fg-2" onClick={() => setRaw((v) => !v)}>
          Showing {raw ? "raw" : "weighted"} share
        </button>
      </div>
      <CompareCard
        metricKey="star_mix"
        glossary={glossary}
        n={(a.overview?.meta?.n_used ?? 0) + (b.overview?.meta?.n_used ?? 0)}
        nameA={nameA}
        nameB={nameB}
        a={<StarBars buckets={sa?.buckets ?? []} color="var(--a)" raw={raw} />}
        b={<StarBars buckets={sb?.buckets ?? []} color="var(--b)" raw={raw} />}
      />
      <Card>
        <h3 className="text-card">The scenario</h3>
        <ul className="mt-2 space-y-2 text-body">
          {(sa?.lines ?? []).length ? (
            (sa.lines as string[]).map((line, i) => (
              <li key={i}>
                {line.replaceAll("{A}", a.overview.meta.company_name)} ·{" "}
                {((sb?.lines?.[i] as string) ?? "").replaceAll("{A}", b.overview.meta.company_name)}
              </li>
            ))
          ) : (
            <li>Not enough analysed reviews to describe the star mix.</li>
          )}
        </ul>
      </Card>
    </section>
  );
}

function StarBars({ buckets, color, raw }: { buckets: AnyRec[]; color: string; raw: boolean }) {
  return (
    <div className="space-y-2">
      {buckets.map((bucket) => {
        const share = raw ? bucket.share_raw : bucket.share_weighted;
        return (
          <div key={bucket.stars}>
            <div className="flex justify-between text-caption text-fg-3">
              <span>{bucket.stars}★</span>
              <span>{formatPct(share)}</span>
            </div>
            <div className="h-3 rounded-control bg-wash">
              <div className="h-full rounded-r-[8px]" style={{ width: `${(share || 0) * 100}%`, background: color }} />
            </div>
            <p className="text-caption text-fg-2">{(bucket.top_themes ?? []).join(", ").replace(/_/g, " ")}</p>
          </div>
        );
      })}
    </div>
  );
}

export function PainSection({
  a,
  b,
  glossary,
  onTheme,
  explanations,
}: {
  a: AnyRec;
  b: AnyRec;
  glossary: Glossary;
  onTheme: (t: string) => void;
  explanations?: Record<string, string>;
}) {
  const empty = !(a.pain_points ?? []).length && !(b.pain_points ?? []).length;
  const nameA = a.overview?.meta?.company_name ?? "A";
  const nameB = b.overview?.meta?.company_name ?? "B";
  if (empty) {
    return <SectionFrame title="What to fix first" empty="No pain points or strengths in this range.">{null}</SectionFrame>;
  }
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-section">What to fix first</h2>
        <p className="mt-1 flex flex-wrap items-center gap-x-2 text-caption text-fg-3">
          <span>Each company&apos;s problems, most urgent at the top. Ranked on its own, so the two lists are not comparable.</span>
          <MetricLabel metricKey="severity" glossary={glossary} />
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <PainCol company={nameA} rows={a.pain_points} color="a" onTheme={onTheme} explanations={explanations} />
        <PainCol company={nameB} rows={b.pain_points} color="b" onTheme={onTheme} explanations={explanations} />
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <StrengthCol company={nameA} rows={a.strengths} color="a" onTheme={onTheme} />
        <StrengthCol company={nameB} rows={b.strengths} color="b" onTheme={onTheme} />
      </div>
    </section>
  );
}

/** "8 in 10" reads faster than "80%" for a share of mentions. */
function inTen(rate: number | null | undefined): string | null {
  if (rate == null || Number.isNaN(rate)) return null;
  const n = Math.round(rate * 10);
  if (n <= 0) return "fewer than 1 in 10";
  if (n >= 10) return "nearly every";
  return `${n} in 10`;
}

/** One plain sentence with the two facts that set the ranking. */
function whyRanked(row: AnyRec): string {
  const parts: string[] = [];
  const share = inTen(row.negative_rate);
  if (share) parts.push(share === "nearly every" ? "Nearly every mention is a complaint" : `Complained about in ${share} mentions`);
  // star_drag is (avg stars when mentioned − overall avg): negative means the theme pulls the rating down
  const drag = typeof row.star_drag === "number" ? row.star_drag : null;
  if (drag != null) {
    if (Math.abs(drag) < 0.05) parts.push("barely moves the rating");
    else if (drag < 0) parts.push(`costs about ${Math.abs(drag).toFixed(1)}★ when it comes up`);
    else parts.push("does not lower the rating");
  }
  return parts.join(" · ");
}

function explanationFor(row: AnyRec, explanations?: Record<string, string>): string {
  if (!explanations) return row.explanation;
  const direct = explanations[row.theme];
  if (direct) return direct;
  const label = String(row.label ?? "").toLowerCase();
  const slug = String(row.theme ?? "").replace(/_/g, " ").toLowerCase();
  const match = Object.entries(explanations).find(([key]) => {
    const k = key.toLowerCase();
    return k.includes(slug) || (label && k.includes(label));
  });
  return match ? match[1] : row.explanation;
}

function PainCol({ company, rows, color, onTheme, explanations }: AnyRec) {
  // "other" is the catch-all bucket; guard here too so older saved snapshots never rank it
  const ranked = [...(rows ?? [])]
    .filter((row: AnyRec) => row.theme !== "other")
    .sort((x: AnyRec, y: AnyRec) => (y.severity ?? 0) - (x.severity ?? 0) || (y.negative_rate ?? 0) - (x.negative_rate ?? 0))
    .slice(0, 5);
  return (
    <Card className={color === "a" ? "border-l-[3px] border-l-a" : "border-l-[3px] border-l-b"}>
      <h3 className={`text-card ${color === "a" ? "text-a" : "text-b"}`}>{company}</h3>
      {ranked.length ? (
        <ol className="mt-3 space-y-4">
          {ranked.map((row: AnyRec, i: number) => (
            <li key={row.theme}>
              <button type="button" className="flex w-full gap-3 text-left" onClick={() => onTheme(row.theme)}>
                <span className="w-5 shrink-0 pt-px text-small text-fg-3" aria-hidden>
                  {i + 1}.
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-small text-fg">{row.label}</span>
                    {i === 0 ? <Pill>Fix first</Pill> : null}
                  </div>
                  <p className="mt-0.5 text-caption text-fg-2">{whyRanked(row)}</p>
                  {explanationFor(row, explanations) ? <p className="mt-1 text-caption">{explanationFor(row, explanations)}</p> : null}
                  {(row.snippets ?? []).slice(0, 2).map((sn: AnyRec, j: number) => (
                    <ArabicText key={j} text={sn.text} textEn={sn.text_en} language={sn.language} />
                  ))}
                </div>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 text-caption text-fg-3">No pain points in this range.</p>
      )}
    </Card>
  );
}

/** Themes are named as problems; when praised they need the positive wording. */
function strengthLabel(row: AnyRec): string {
  return row.positive_label || `${row.label} (praised)`;
}

function StrengthCol({ company, rows, color, onTheme }: AnyRec) {
  // guard for older saved snapshots that were stored before the API applied the floor
  const shown = (rows ?? []).filter((row: AnyRec) => row.theme !== "other" && (row.positive_rate ?? 0) >= 0.5);
  return (
    <Card className={color === "a" ? "border-l-[3px] border-l-a" : "border-l-[3px] border-l-b"}>
      <h3 className={`text-card ${color === "a" ? "text-a" : "text-b"}`}>{company} · what customers praise</h3>
      {shown.length ? (
        <ul className="mt-3 space-y-3">
          {shown.map((row: AnyRec) => {
            const share = inTen(row.positive_rate);
            const n = typeof row.n_mentions === "number" ? row.n_mentions : null;
            return (
              <li key={row.theme}>
                <button type="button" className="block w-full text-left" onClick={() => onTheme(row.theme)}>
                  <span className="text-small text-fg">{strengthLabel(row)}</span>
                  <span className="mt-0.5 block text-caption text-fg-2">
                    {share === "nearly every" ? "Nearly every mention is praise" : `Praised in ${share} mentions`}
                    {n != null ? ` · ${n} ${n === 1 ? "review mentions" : "reviews mention"} it` : ""}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="mt-3 text-caption text-fg-3">No clear strengths yet: nothing is praised more often than it is criticised.</p>
      )}
    </Card>
  );
}

const STAGE_LABELS: Record<string, string> = {
  discover_browse: "Discover",
  order_checkout: "Order",
  wait_track: "Wait",
  receive: "Receive",
  recover_support: "Recover",
};

const KANO_LABELS: Record<string, string> = {
  must_be: "Basic expectation",
  performance: "Better is better",
  delighter: "Nice surprise",
};

export function JourneySection({ data, glossary, onTheme, loading, reads, nameA = "A", nameB = "B" }: AnyRec) {
  const names: Record<string, string> = { a: nameA, b: nameB };
  const labels = STAGE_LABELS;
  const order = ["discover_browse", "order_checkout", "wait_track", "receive", "recover_support"];
  // per stage, which company is more negative; ties within 1 point are left unmarked
  const worseAt: Record<string, "a" | "b" | null> = {};
  if (data) {
    const rateOf = (side: "a" | "b", stage: string): number | null => {
      const cell = (data[side]?.cells ?? []).find((c: AnyRec) => c.stage === stage);
      return typeof cell?.negative_rate === "number" ? cell.negative_rate : null;
    };
    for (const stage of order) {
      const ra = rateOf("a", stage);
      const rb = rateOf("b", stage);
      worseAt[stage] = ra == null || rb == null || Math.abs(ra - rb) < 0.01 ? null : ra > rb ? "a" : "b";
    }
  }
  return (
    <SectionFrame title="Where the experience breaks" loading={loading} empty={!data && !loading ? "Journey map is not available yet." : undefined}>
      {data ? (
        <>
          <CompanyLegend nameA={nameA} nameB={nameB} sides={false} note="One row per company, stages Discover → Order → Wait → Receive → Recover." />
          <p className="flex flex-wrap items-center gap-x-3 text-caption text-fg-3">
            <MetricLabel metricKey="negative_pct" glossary={glossary} />
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-pill bg-bad" aria-hidden />
              Red = the more negative of the two companies at that stage
            </span>
          </p>
          {["a", "b"].map((side) => (
            <div key={side}>
              <p className={`mb-2 text-caption font-medium ${side === "a" ? "text-a" : "text-b"}`}>{names[side]}</p>
              <div className="grid gap-2 md:grid-cols-5">
              {(data[side]?.cells ?? []).map((cell: AnyRec) => {
                const worse = worseAt[cell.stage] === side;
                const other = side === "a" ? nameB : nameA;
                return (
                <button
                  key={cell.stage}
                  type="button"
                  onClick={() => cell.top_theme && onTheme(cell.top_theme)}
                  className={`rounded-card border p-4 text-left ${worse ? "border-bad" : cell.stage === data[side].peak_stage ? "border-fg" : "border-border"} ${side === "a" ? "border-l-[3px] border-l-a" : "border-l-[3px] border-l-b"}`}
                  aria-label={`${labels[cell.stage]}: ${formatPct(cell.negative_rate)} negative${worse ? `, more negative than ${other}` : ""}`}
                >
                  <p className="text-caption text-fg-3">{labels[cell.stage]}</p>
                  <p className={`text-card ${worse ? "text-bad" : ""}`}>{formatPct(cell.negative_rate)}</p>
                  {worse ? <p className="text-caption text-bad">Worse than {other}</p> : null}
                  <p className="text-caption text-fg-2">{formatPct(cell.complaint_share)} of complaints</p>
                  <p className="text-caption">{(cell.top_theme ?? "").replace(/_/g, " ")}</p>
                  {cell.snippet ? <ArabicText text={cell.snippet.text} textEn={cell.snippet.text_en} language={cell.snippet.language} /> : null}
                </button>
                );
              })}
              </div>
            </div>
          ))}
          {reads ? (
            <div className="space-y-2">
              {order.map((stage) =>
                reads[stage] ? (
                  <p key={stage} className="text-small text-fg-2">
                    {labels[stage]}: {reads[stage]}
                  </p>
                ) : null,
              )}
            </div>
          ) : null}
        </>
      ) : null}
    </SectionFrame>
  );
}

export function KanoSection({ data, glossary, loading, nameA = "A", nameB = "B" }: AnyRec) {
  const names: Record<string, string> = { a: nameA, b: nameB };
  return (
    <SectionFrame title="Basics vs differentiators" loading={loading} empty={!data && !loading ? "Kano bands are not available yet." : undefined}>
      {data ? (
        <>
          {data.promo_ended_rising ? (
            <p className="text-small text-fg-2">Promotions look like they are turning from a delighter into a must-be.</p>
          ) : null}
          <div className="grid gap-6 md:grid-cols-2">
            {["a", "b"].map((side) => (
              <Card key={side} className={side === "a" ? "border-l-[3px] border-l-a" : "border-l-[3px] border-l-b"}>
                <h3 className={`mb-3 text-card ${side === "a" ? "text-a" : "text-b"}`}>{names[side]}</h3>
                {(data[side]?.classes ?? []).map((row: AnyRec) => (
                  <div key={row.kano} className="mb-3">
                    <MetricLabel metricKey="negative_pct" glossary={glossary} />
                    <p className="text-small">
                      {String(row.kano).replace("_", "-")}: {formatPct(row.negative_rate)} negative · {formatPct(row.complaint_share)} of complaints
                    </p>
                    <p className="text-caption text-fg-2">{(row.themes ?? []).join(", ").replace(/_/g, " ")}</p>
                  </div>
                ))}
              </Card>
            ))}
          </div>
        </>
      ) : null}
    </SectionFrame>
  );
}

export function ThemeSection({ a, b, glossary, onTheme }: { a: AnyRec; b: AnyRec; glossary: Glossary; onTheme: (t: string) => void }) {
  // union of both companies' themes, so the list is the same whichever company is chosen first
  const byB = Object.fromEntries((b.theme_matrix ?? []).map((r: AnyRec) => [r.theme, r]));
  const seen = new Set<string>();
  const rows: AnyRec[] = [];
  for (const r of [...(a.theme_matrix ?? []), ...(b.theme_matrix ?? [])] as AnyRec[]) {
    if (seen.has(r.theme)) continue;
    seen.add(r.theme);
    // a theme only B mentions still gets a row; its A-side rate is unknown, not zero
    rows.push((a.theme_matrix ?? []).some((x: AnyRec) => x.theme === r.theme) ? r : { ...r, negative_rate: null });
  }
  // "other" is the catch-all bucket; it is not a theme anyone can compare on
  const radar = rows
    .filter((row: AnyRec) => row.theme !== "other")
    .map((row: AnyRec) => ({
      theme: row.label,
      a: (row.negative_rate ?? 0) * 100,
      b: ((byB[row.theme]?.negative_rate as number) ?? 0) * 100,
    }));
  const nameA = a.overview?.meta?.company_name ?? "A";
  const nameB = b.overview?.meta?.company_name ?? "B";
  if (!rows.length) return <SectionFrame title="Theme by theme" empty="No theme matrix for this range.">{null}</SectionFrame>;
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-section">Theme by theme</h2>
        <CompanyLegend nameA={nameA} nameB={nameB} sides={false} note="Negative % per theme; further out is worse." />
      </div>
      <Card>
        <div className="h-[420px] md:h-[600px]">
          <ResponsiveContainer>
            <RadarChart data={radar} outerRadius="78%" margin={{ top: 24, right: 48, bottom: 24, left: 48 }}>
              <PolarGrid stroke="var(--divider)" />
              <PolarAngleAxis dataKey="theme" tick={{ fontSize: 13, fill: "var(--fg-2)" }} />
              <PolarRadiusAxis
                angle={75}
                domain={[0, 100]}
                tickCount={5}
                axisLine={false}
                tick={{ fontSize: 11, fill: "var(--fg-3)" }}
                tickFormatter={(v: number) => (v === 0 ? "" : `${v}%`)}
              />
              <Radar dataKey="a" name={nameA} stroke="var(--a)" strokeWidth={2} fill="var(--a)" fillOpacity={0.15} />
              <Radar dataKey="b" name={nameB} stroke="var(--b)" strokeWidth={2} fill="var(--b)" fillOpacity={0.15} />
              <Tooltip
                formatter={(value: number) => `${Number(value).toFixed(1)}% negative`}
                contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: "var(--border)" }}
              />
              <Legend wrapperStyle={{ fontSize: 13, color: "var(--fg-2)" }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
        <p>
          <a href="#theme-table" className="text-caption text-fg-3">
            View as table
          </a>
        </p>
      </Card>
      <ThemeTable rows={rows} byB={byB} nameA={nameA} nameB={nameB} glossary={glossary} onTheme={onTheme} />
    </section>
  );
}

// ties within 2 points are not called out; "gap" is in percentage points, positive = A is worse
const THEME_TIE_PTS = 2;

function ThemeTable({ rows, byB, nameA, nameB, glossary, onTheme }: AnyRec) {
  type Item = { theme: string; label: string; journey_stage?: string; kano?: string; ra: number | null; rb: number | null; gap: number | null; worse: "a" | "b" | null };
  const items: Item[] = (rows as AnyRec[])
    .filter((row) => row.theme !== "other")
    .map((row): Item => {
      const ra = typeof row.negative_rate === "number" ? row.negative_rate * 100 : null;
      const rbRaw = byB[row.theme]?.negative_rate;
      const rb = typeof rbRaw === "number" ? rbRaw * 100 : null;
      const gap = ra != null && rb != null ? ra - rb : null;
      const worse: "a" | "b" | null = gap == null || Math.abs(gap) < THEME_TIE_PTS ? null : gap > 0 ? "a" : "b";
      return { theme: row.theme, label: row.label, journey_stage: row.journey_stage, kano: row.kano, ra, rb, gap, worse };
    })
    .sort((x, y) => Math.abs(y.gap ?? -1) - Math.abs(x.gap ?? -1) || Math.max(y.ra ?? 0, y.rb ?? 0) - Math.max(x.ra ?? 0, x.rb ?? 0));

  const worseA = items.filter((r) => r.worse === "a").length;
  const worseB = items.filter((r) => r.worse === "b").length;
  const top = items.find((r) => r.worse);
  const summary = (() => {
    if (!items.length) return null;
    if (!top) return "Both companies are within a couple of points on every theme.";
    const lead = worseA === worseB ? `Each company is worse on ${worseA} of ${items.length} themes` : worseA > worseB ? `${nameA} is worse on ${worseA} of ${items.length} themes` : `${nameB} is worse on ${worseB} of ${items.length} themes`;
    const who = top.worse === "a" ? nameA : nameB;
    return `${lead}. Biggest gap: ${top.label}, where ${who} is ${Math.round(Math.abs(top.gap ?? 0))} pts more negative.`;
  })();

  const pct = (v: number | null) => (v == null ? "—" : `${v.toFixed(0)}%`);
  // bars are scaled to the biggest gap on the page so the top row always fills half the track
  const maxGap = Math.max(1, ...items.map((r) => Math.abs(r.gap ?? 0)));

  // one bar per theme, centred at zero: grows left (A's colour) when A is worse, right (B's colour) when B is worse
  const GapBar = ({ gap, worse }: { gap: number | null; worse: "a" | "b" | null }) => {
    const half = gap == null ? 0 : (Math.abs(gap) / maxGap) * 50;
    return (
      <div className="relative h-3 w-full" aria-hidden>
        <div className="absolute inset-y-0 left-0 right-1/2 rounded-l-pill bg-divider" />
        <div className="absolute inset-y-0 left-1/2 right-0 rounded-r-pill bg-divider" />
        {worse === "a" ? <div className="absolute inset-y-0 rounded-l-pill bg-a" style={{ right: "50%", width: `${half}%` }} /> : null}
        {worse === "b" ? <div className="absolute inset-y-0 rounded-r-pill bg-b" style={{ left: "50%", width: `${half}%` }} /> : null}
        <div className="absolute inset-y-[-3px] left-1/2 w-px -translate-x-1/2 bg-fg-3" />
      </div>
    );
  };

  const verdict = (row: Item) => {
    if (row.gap == null) return { text: "No data", tone: "text-fg-3" };
    if (!row.worse) return { text: "About the same", tone: "text-fg-3" };
    return { text: `${row.worse === "a" ? nameA : nameB} worse by ${Math.round(Math.abs(row.gap))} pts`, tone: "text-bad" };
  };

  return (
    <Card>
      <div className="mb-3">
        <p className="text-caption text-fg-3">
          Who is worse on each theme, biggest difference first. The bar shows the gap in <MetricLabel metricKey="negative_pct" glossary={glossary} /> between the two companies; the longer the bar, the bigger the gap.
        </p>
        {summary ? <p className="mt-1 text-small text-fg">{summary}</p> : null}
      </div>
      <table id="theme-table" className="w-full table-fixed text-left">
        <thead className="text-caption text-fg-3">
          <tr className="h-11 border-b border-divider">
            <th className="w-[32%] px-3 font-normal sm:w-[28%]">Theme</th>
            <th className="px-3 font-normal">
              <div className="flex justify-between">
                <span className="text-a">← {nameA} worse</span>
                <span className="text-b">{nameB} worse →</span>
              </div>
            </th>
            <th className="hidden w-[26%] px-3 font-normal sm:table-cell">Verdict</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => {
            const v = verdict(row);
            return (
              <tr key={row.theme} className="cursor-pointer border-t border-divider hover:bg-wash" onClick={() => onTheme(row.theme)}>
                <td className="px-3 py-3">
                  <p className="text-small text-fg">{row.label}</p>
                  <p className="text-caption text-fg-3">
                    {[row.journey_stage && (STAGE_LABELS[row.journey_stage] ?? row.journey_stage), row.kano && (KANO_LABELS[row.kano] ?? row.kano)]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </td>
                <td className="px-3 py-3 align-middle">
                  <GapBar gap={row.gap} worse={row.worse} />
                  <p className={`mt-1.5 text-caption sm:hidden ${v.tone}`}>{v.text}</p>
                  <p className="text-caption text-fg-3 sm:hidden">
                    {pct(row.ra)} vs {pct(row.rb)} negative
                  </p>
                </td>
                <td className="hidden px-3 py-3 sm:table-cell">
                  <p className={`text-small ${v.tone}`}>{v.text}</p>
                  <p className="text-caption text-fg-3">
                    {pct(row.ra)} vs {pct(row.rb)} negative
                  </p>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

export function IpaSection({ data, onTheme, glossary, loading, nameA = "A", nameB = "B" }: AnyRec) {
  const quad = (q?: string) => String(q ?? "").replace(/_/g, " ");
  const tickStyle = { fontSize: 12, fill: "var(--fg-3)" };
  const points = (data?.a ?? []).map((p: AnyRec) => {
    const other = (data?.b ?? []).find((x: AnyRec) => x.theme === p.theme);
    return {
      theme: p.theme,
      label: p.label,
      aX: p.mention_share,
      aY: p.net_sentiment_within_mentions,
      bX: other?.mention_share,
      bY: other?.net_sentiment_within_mentions,
      aQ: p.quadrant,
      bQ: other?.quadrant,
    };
  });
  return (
    <SectionFrame title="Fix now / Protect" loading={loading} empty={!data && !loading ? "Importance–performance data is not available yet." : undefined}>
      {data ? (
        <>
          <MetricLabel metricKey="severity" glossary={glossary} />
          <CompanyLegend
            nameA={nameA}
            nameB={nameB}
            sides={false}
            note="Each dot is a theme. Right = mentioned more often; down = talked about more negatively."
          />
          <Card>
            <p className="mb-2 text-caption text-fg-3">
              Bottom-right is Fix now (common and negative) · top-right is Protect (common and positive) · bottom-left is Monitor · top-left is Nice to have.
            </p>
            <div className="h-80">
              <ResponsiveContainer>
                <ScatterChart margin={{ top: 8, right: 16, bottom: 28, left: 8 }}>
                  <XAxis
                    type="number"
                    dataKey="x"
                    name="Share of reviews mentioning it"
                    tick={tickStyle}
                    tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                    label={{ value: "Share of reviews mentioning the theme", position: "insideBottom", offset: -12, fontSize: 12, fill: "var(--fg-3)" }}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    name="Net sentiment within those mentions"
                    tick={tickStyle}
                    domain={[-1, 1]}
                    label={{ value: "Net sentiment", angle: -90, position: "insideLeft", fontSize: 12, fill: "var(--fg-3)" }}
                  />
                  <ReferenceLine y={0} stroke="var(--divider)" />
                  <ReferenceLine x={data.mention_threshold ?? 0} stroke="var(--divider)" />
                  <ZAxis range={[40, 40]} />
                  <Tooltip
                    formatter={(value: any, key: any) => [
                      key === "Share of reviews mentioning it" ? `${(Number(value) * 100).toFixed(1)}%` : Number(value).toFixed(2),
                      key,
                    ]}
                    labelFormatter={() => ""}
                    content={({ payload }: AnyRec) => {
                      const pt = payload?.[0]?.payload;
                      if (!pt) return null;
                      return (
                        <div className="rounded-control border border-border bg-bg p-2 text-caption text-fg">
                          <p className="text-small">{pt.name}</p>
                          <p className="text-fg-2">{pt.company}</p>
                          <p>Mentioned in {(pt.x * 100).toFixed(1)}% of reviews · net sentiment {pt.y.toFixed(2)}</p>
                          <p className="text-fg-2">{quad(pt.quadrant)}</p>
                        </div>
                      );
                    }}
                  />
                  <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 12, color: "var(--fg-2)" }} />
                  <Scatter
                    name={nameA}
                    data={points.map((p: AnyRec) => ({ x: p.aX, y: p.aY, name: p.label, company: nameA, quadrant: p.aQ }))}
                    fill="var(--a)"
                    onClick={(e: AnyRec) => e?.name && onTheme(points.find((p: AnyRec) => p.label === e.name)?.theme)}
                  />
                  <Scatter
                    name={nameB}
                    data={points
                      .filter((p: AnyRec) => p.bX != null)
                      .map((p: AnyRec) => ({ x: p.bX, y: p.bY, name: p.label, company: nameB, quadrant: p.bQ }))}
                    fill="var(--b)"
                    onClick={(e: AnyRec) => e?.name && onTheme(points.find((p: AnyRec) => p.label === e.name)?.theme)}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {points.map((p: AnyRec) => (
                <button key={p.theme} type="button" className="text-left text-small" onClick={() => onTheme(p.theme)}>
                  <span className="text-fg">{p.label}</span>
                  <span className="text-fg-2">
                    {" — "}
                    <span className="text-a">{nameA}</span> {quad(p.aQ)}
                    {p.bQ ? (
                      <>
                        {" · "}
                        <span className="text-b">{nameB}</span> {quad(p.bQ)}
                      </>
                    ) : null}
                  </span>
                </button>
              ))}
            </div>
          </Card>
        </>
      ) : null}
    </SectionFrame>
  );
}

// ---- Trends: direction (are we getting better or worse) and turning points (when did it change) ----

type WeekPoint = { week: string; neg: number | null; vol: number };

// volume-weighted centred 3-week average; damps weeks with only a handful of reviews
function smoothWeeks(points: WeekPoint[]): (number | null)[] {
  return points.map((_, i) => {
    let num = 0;
    let den = 0;
    for (let j = Math.max(0, i - 1); j <= Math.min(points.length - 1, i + 1); j++) {
      const p = points[j];
      if (p.neg == null || !p.vol) continue;
      num += p.neg * p.vol;
      den += p.vol;
    }
    return den ? num / den : null;
  });
}

const TURN_MIN_PTS = 15;
const TURN_MIN_REVIEWS = 3;

type Turn = { week: string; from: number; to: number; sustained: boolean };

// the single biggest sustained jump in the smoothed line: where it "broke" (or recovered)
function findTurningPoint(points: WeekPoint[], smooth: (number | null)[]): Turn | null {
  let best: Turn | null = null;
  for (let i = 1; i < smooth.length; i++) {
    const prev = smooth[i - 1];
    const cur = smooth[i];
    if (prev == null || cur == null || points[i].vol < TURN_MIN_REVIEWS) continue;
    const jump = cur - prev;
    if (Math.abs(jump) < TURN_MIN_PTS) continue;
    const after = smooth.slice(i + 1, i + 4).filter((v): v is number => v != null);
    // sustained = the following weeks stay at least halfway across the jump; the latest week has no "after" yet
    const held = after.every((v) => (jump > 0 ? v >= prev + jump / 2 : v <= prev + jump / 2));
    if (after.length && !held) continue;
    const sustained = after.length > 0;
    const cand = { week: points[i].week, from: prev, to: cur, sustained };
    // a confirmed turning point beats a fresh, unconfirmed one; otherwise the bigger jump wins
    if (!best || (cand.sustained && !best.sustained) || (cand.sustained === best.sustained && Math.abs(jump) > Math.abs(best.to - best.from))) best = cand;
  }
  return best;
}

function weekLabel(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

type Momentum = { last: number | null; prior: number | null; lastVol: number; priorVol: number; windowLabel: string };

// prefer the API's 30-day windows; fall back to 4-week windows from the series for older saved snapshots
function momentumOf(trends: AnyRec, points: WeekPoint[]): Momentum | null {
  const m = trends?.momentum;
  if (m?.last && m?.prior) {
    return {
      last: typeof m.last.negative_pct === "number" ? m.last.negative_pct * 100 : null,
      prior: typeof m.prior.negative_pct === "number" ? m.prior.negative_pct * 100 : null,
      lastVol: m.last.volume ?? 0,
      priorVol: m.prior.volume ?? 0,
      windowLabel: `last ${m.window_days ?? 30} days`,
    };
  }
  if (points.length < 2) return null;
  const agg = (ps: WeekPoint[]) => {
    const den = ps.reduce((s, p) => s + (p.neg == null ? 0 : p.vol), 0);
    const num = ps.reduce((s, p) => s + (p.neg == null ? 0 : p.neg * p.vol), 0);
    return { pct: den ? num / den : null, vol: ps.reduce((s, p) => s + p.vol, 0) };
  };
  const last = agg(points.slice(-4));
  const prior = agg(points.slice(-8, -4));
  return { last: last.pct, prior: prior.pct, lastVol: last.vol, priorVol: prior.vol, windowLabel: "last 4 weeks" };
}

function direction(m: Momentum | null): { verb: "worse" | "better" | "flat" | "unknown"; delta: number | null } {
  if (!m || m.last == null || m.prior == null) return { verb: "unknown", delta: null };
  const delta = m.last - m.prior;
  if (Math.abs(delta) < 2) return { verb: "flat", delta };
  return { verb: delta > 0 ? "worse" : "better", delta };
}

function DirectionCard({ name, side, m, glossary }: { name: string; side: "a" | "b"; m: Momentum | null; glossary: Glossary }) {
  const d = direction(m);
  const tone = d.verb === "worse" ? "text-bad" : d.verb === "better" ? "text-good" : "text-fg-2";
  const arrow = d.verb === "worse" ? "↑" : d.verb === "better" ? "↓" : "→";
  return (
    <Card className={side === "a" ? "border-l-[3px] border-l-a" : "border-l-[3px] border-l-b"}>
      <div className="flex items-center justify-between gap-2">
        <h3 className={`text-card ${side === "a" ? "text-a" : "text-b"}`}>{name}</h3>
        <MetricLabel metricKey="momentum" glossary={glossary} />
      </div>
      {m && m.last != null ? (
        <>
          <p className="mt-2 text-caption text-fg-3">Negative %, {m.windowLabel}</p>
          <p className="text-kpi">
            {m.last.toFixed(0)}%{" "}
            <span className={`text-card ${tone}`}>
              {arrow} {d.delta == null ? "" : `${Math.abs(d.delta).toFixed(0)} pts`}
            </span>
          </p>
          <p className={`text-small ${tone}`}>
            {d.verb === "worse"
              ? `Getting worse: was ${m.prior?.toFixed(0)}% in the period before`
              : d.verb === "better"
                ? `Improving: was ${m.prior?.toFixed(0)}% in the period before`
                : d.verb === "flat"
                  ? `Holding steady: was ${m.prior?.toFixed(0)}% in the period before`
                  : "Not enough earlier reviews to compare"}
          </p>
          <p className="mt-1 text-caption text-fg-3">
            {m.lastVol} {m.lastVol === 1 ? "review" : "reviews"} in this period · {m.priorVol} in the one before
          </p>
        </>
      ) : (
        <p className="mt-2 text-caption text-fg-3">No reviews in the {m?.windowLabel ?? "recent period"}.</p>
      )}
    </Card>
  );
}

export function TrendsSection({ a, b, glossary }: { a: AnyRec; b: AnyRec; glossary: Glossary }) {
  const nameA = a.overview?.meta?.company_name ?? "A";
  const nameB = b.overview?.meta?.company_name ?? "B";
  const toPoints = (series: AnyRec[], weeks: string[]): WeekPoint[] => {
    const by = Object.fromEntries(series.map((s: AnyRec) => [s.week, s]));
    return weeks.map((week) => ({
      week,
      neg: typeof by[week]?.negative_pct === "number" ? by[week].negative_pct * 100 : null,
      vol: by[week]?.volume ?? 0,
    }));
  };
  const seriesA: AnyRec[] = a.trends?.series ?? [];
  const seriesB: AnyRec[] = b.trends?.series ?? [];
  const weeks = Array.from(new Set([...seriesA.map((s) => s.week), ...seriesB.map((s) => s.week)])).sort();
  if (!weeks.length) return <SectionFrame title="Trends" empty="No trend series in this range.">{null}</SectionFrame>;

  const pA = toPoints(seriesA, weeks);
  const pB = toPoints(seriesB, weeks);
  const sA = smoothWeeks(pA);
  const sB = smoothWeeks(pB);
  const turnA = findTurningPoint(pA, sA);
  const turnB = findTurningPoint(pB, sB);
  const mA = momentumOf(a.trends, pA);
  const mB = momentumOf(b.trends, pB);
  const dA = direction(mA);
  const dB = direction(mB);

  const chart = weeks.map((week, i) => ({ week, a: sA[i], b: sB[i], aVol: pA[i].vol, bVol: pB[i].vol }));

  const sentence = (name: string, m: Momentum | null, d: ReturnType<typeof direction>) => {
    if (!m || m.last == null || m.prior == null) return `${name}: not enough reviews to read a direction.`;
    const span = `${m.prior.toFixed(0)}% → ${m.last.toFixed(0)}% negative`;
    if (d.verb === "worse") return `${name} is getting worse (${span}).`;
    if (d.verb === "better") return `${name} is improving (${span}).`;
    return `${name} is holding steady (${span}).`;
  };
  const turnSentence = (name: string, t: Turn | null) => {
    if (!t) return `${name}: no sharp turning point; changes have been gradual.`;
    const up = t.to > t.from;
    const move = `negative % ${up ? "jumped" : "fell"} from ${t.from.toFixed(0)}% to ${t.to.toFixed(0)}%`;
    if (!t.sustained) return `${name}: ${move} in the most recent week (${weekLabel(t.week)}). Too early to know if it holds.`;
    return `${name} ${up ? "broke" : "recovered"} in the week of ${weekLabel(t.week)}: ${move} and stayed there.`;
  };

  const tickStyle = { fontSize: 12, fill: "var(--fg-3)" };
  const tooltip = (value: any, key: any, item: any) => {
    const side = key === "a" ? "a" : "b";
    const vol = item?.payload?.[side === "a" ? "aVol" : "bVol"] ?? 0;
    return [typeof value === "number" ? `${value.toFixed(0)}% negative · ${vol} ${vol === 1 ? "review" : "reviews"} this week` : "—", side === "a" ? nameA : nameB];
  };

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-section">Is it getting better or worse?</h2>
        <CompanyLegend nameA={nameA} nameB={nameB} sides={false} note="Negative % by week, 3-week average. Up is worse. Marked dots are turning points." />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <DirectionCard name={nameA} side="a" m={mA} glossary={glossary} />
        <DirectionCard name={nameB} side="b" m={mB} glossary={glossary} />
      </div>

      <Card>
        <p className="text-small text-fg">
          {sentence(nameA, mA, dA)} {sentence(nameB, mB, dB)}
        </p>
        <div className="mt-3 h-72">
          <ResponsiveContainer>
            <LineChart data={chart} margin={{ top: 16, right: 16, bottom: 0, left: -12 }}>
              <XAxis dataKey="week" tick={tickStyle} tickFormatter={weekLabel} minTickGap={24} />
              <YAxis domain={[0, 100]} tick={tickStyle} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip labelFormatter={(w) => `Week of ${weekLabel(String(w))}`} formatter={tooltip} contentStyle={{ fontSize: 13, borderRadius: 6, borderColor: "var(--border)" }} />
              {turnA ? <ReferenceLine x={turnA.week} stroke="var(--a)" strokeDasharray="3 3" /> : null}
              {turnB ? <ReferenceLine x={turnB.week} stroke="var(--b)" strokeDasharray="3 3" /> : null}
              <Line type="monotone" dataKey="a" name={nameA} stroke="var(--a)" strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="b" name={nameB} stroke="var(--b)" strokeWidth={2} dot={false} connectNulls />
              {turnA ? <ReferenceDot x={turnA.week} y={turnA.to} r={5} fill="var(--a)" stroke="var(--bg)" strokeWidth={2} /> : null}
              {turnB ? <ReferenceDot x={turnB.week} y={turnB.to} r={5} fill="var(--b)" stroke="var(--bg)" strokeWidth={2} /> : null}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-3 space-y-1">
          <p className="text-caption text-fg-3">Turning points</p>
          <p className="text-small text-fg-2">
            <span className="text-a">●</span> {turnSentence(nameA, turnA)}
          </p>
          <p className="text-small text-fg-2">
            <span className="text-b">●</span> {turnSentence(nameB, turnB)}
          </p>
          <p className="text-caption text-fg-3">A turning point is a jump of {TURN_MIN_PTS}+ points that held for the following weeks. Something happened that week; the review text for it is one click away in the theme drawer.</p>
        </div>
      </Card>
    </section>
  );
}

export function CompetitorSection({ a, b, glossary }: { a: AnyRec; b: AnyRec; glossary: Glossary }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-section">Who is about to leave</h2>
        <p className="mt-1 text-caption text-fg-3">Of each company&apos;s negative reviews, the share where the writer says they are uninstalling or switching. Higher is worse.</p>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        {[a, b].map((side: AnyRec, i: number) => (
          <Card key={side.overview.meta.company_slug} className={`space-y-2 border-l-[3px] ${i === 0 ? "border-l-a" : "border-l-b"}`}>
            <h3 className={`text-card ${i === 0 ? "text-a" : "text-b"}`}>{side.overview.meta.company_name}</h3>
            <MetricLabel metricKey="churn_signal" glossary={glossary} n={side.overview.meta.n_used} />
            <p className="text-kpi">{formatPct(side.overview.churn_signal?.value)}</p>
            <p className="text-caption text-fg-3">of negative reviews say they are leaving</p>
          </Card>
        ))}
      </div>
    </section>
  );
}

export function PmSection({
  summary,
  loading,
  onTheme,
  onRegen,
  nameA = "A",
  nameB = "B",
}: {
  summary?: AnyRec;
  loading?: boolean;
  onTheme: (t: string) => void;
  onRegen: () => void;
  nameA?: string;
  nameB?: string;
}) {
  return (
    <SectionFrame title="What a PM should do" loading={loading} empty={!summary && !loading ? "Run summarise to generate PM actions." : undefined}>
      {summary ? (
        <Card className="space-y-4 text-body">
          {summary.kano_read ? <p className="text-small text-fg-2">{summary.kano_read}</p> : null}
          <h3 className="text-card">Differentiators</h3>
          <ul className="list-disc pl-5">
            {(summary.key_differentiators ?? []).map((x: string) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
          <h3 className="text-card">What {nameA} does that {nameB} does not</h3>
          <ul className="list-disc pl-5">
            {(summary.what_a_does_that_b_doesnt ?? []).map((x: string) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
          <h3 className="text-card">What {nameB} does that {nameA} does not</h3>
          <ul className="list-disc pl-5">
            {(summary.what_b_does_that_a_doesnt ?? []).map((x: string) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
          <h3 className="text-card">PM actions</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="border-l-[3px] border-a pl-3">
              <p className="mb-1 text-caption font-medium text-a">{nameA}</p>
              <ul className="list-disc pl-5">
                {(summary.pm_actions_a ?? []).map((x: string) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
            <div className="border-l-[3px] border-b pl-3">
              <p className="mb-1 text-caption font-medium text-b">{nameB}</p>
              <ul className="list-disc pl-5">
                {(summary.pm_actions_b ?? []).map((x: string) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          </div>
          <ul className="list-disc pl-5 text-small text-fg-2">
            {(summary.caveats ?? []).map((x: string) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-2">
            {(summary.watch_list ?? []).map((t: string) => (
              <button key={t} type="button" className="text-small underline" onClick={() => onTheme(t)}>
                {t.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          <p className="text-caption text-fg-3">
            {summary.model_id} · {summary.generated_at} ·{" "}
            <button type="button" className="underline" onClick={onRegen}>
              Regenerate
            </button>
          </p>
        </Card>
      ) : null}
    </SectionFrame>
  );
}

export function MoreDetail({
  a,
  b,
  glossary,
  stateA,
  q,
  onExplore,
  open,
  setOpen,
}: {
  a: AnyRec;
  b: AnyRec;
  glossary: Glossary;
  stateA: string;
  q: string;
  onExplore: (extra: AnyRec) => void;
  open: boolean;
  setOpen: (v: boolean) => void;
}) {
  return (
    <section id="more-detail" className="space-y-4">
      <button type="button" className="flex w-full items-center justify-between text-left" onClick={() => setOpen(!open)}>
        <h2 className="text-section">More detail</h2>
        <span className="text-small text-fg-2">{open ? "Collapse" : "Expand"}</span>
      </button>
      <p className="text-caption text-fg-3">
        Language gap, developer response, complaint concentration, backlog feed, data quality, and the review explorer.
      </p>
      {open ? (
        <div className="space-y-6">
          <Card>
            <h3 className="text-card">Language gap</h3>
            {["a", "b"].map((side) => {
              const gap = (side === "a" ? a : b).language_gap ?? {};
              return (
                <p key={side} className="text-small">
                  {side.toUpperCase()} EN {formatPct(gap.en?.negative_pct)} negative · AR {formatPct(gap.ar?.negative_pct)} negative
                </p>
              );
            })}
          </Card>
          <Card>
            <MetricLabel metricKey="developer_response_rate" glossary={glossary} />
            <p className="text-body">
              {formatPct(a.overview.developer_response_rate?.value)} vs {formatPct(b.overview.developer_response_rate?.value)} · median{" "}
              {a.overview.developer_reply_hours?.toFixed?.(0) ?? "—"} hours
            </p>
          </Card>
          <Card>
            <MetricLabel metricKey="complaint_concentration" glossary={glossary} />
            <p className="text-body">
              Top 3 = {formatPct(a.complaint_concentration?.top_3)} vs {formatPct(b.complaint_concentration?.top_3)}
            </p>
          </Card>
          <Card>
            <h3 className="text-card">Feedback-type backlog</h3>
            {Object.entries(a.feedback_types?.backlog ?? {}).length === 0 ? (
              <p className="text-caption text-fg-3">No feature requests or bug reports in this range.</p>
            ) : (
              Object.entries(a.feedback_types.backlog).map(([theme, items]: any) => (
                <div key={theme} className="mt-3">
                  <button type="button" className="text-small underline" onClick={() => onExplore({ theme })}>
                    {theme.replace(/_/g, " ")}
                  </button>
                  {(items as AnyRec[]).slice(0, 3).map((sn, i) => (
                    <ArabicText key={i} text={sn.text} textEn={sn.text_en} language={sn.language} />
                  ))}
                </div>
              ))
            )}
          </Card>
          <Card id="data-quality">
            <h3 className="text-card">Data quality</h3>
            <MetricLabel metricKey="agreement_rate" glossary={glossary} />
            <p className="text-body">
              <span className="text-a">{a.overview.meta.company_name}</span> {formatPct(a.overview.agreement_rate?.value)} ·{" "}
              <span className="text-b">{b.overview.meta.company_name}</span> {formatPct(b.overview.agreement_rate?.value)}
            </p>
            <p className="mt-3 text-body">
              Exclude flagged is always on: empty praise, contradictory ratings, suspected incentivized reviews, and failed parsing are removed
              before any number is calculated. Weighted is always on: the remaining sample is reweighted to the real star mix so percentages
              match what customers actually rate, not the scrape sample.
            </p>
            <p className="mt-2 text-caption text-fg-2">
              Excluded: {a.overview.meta.company_name} {a.overview.reviews_excluded} · {b.overview.meta.company_name} {b.overview.reviews_excluded}. Reasons:{" "}
              {JSON.stringify(a.overview.exclusion_reasons ?? {})}
            </p>
          </Card>
          <Explorer company={stateA} q={q} extra={{}} />
        </div>
      ) : null}
    </section>
  );
}

export function Explorer({ company, extra, q }: { company: string; extra: AnyRec; q: string }) {
  const [language, setLanguage] = useState(extra.language ?? "");
  const [stars, setStars] = useState(extra.stars ?? "");
  const [theme, setTheme] = useState(extra.theme ?? "");
  const params = new URLSearchParams(q);
  params.set("company", company);
  if (theme) params.set("theme", theme);
  if (extra.sentiment) params.set("sentiment", extra.sentiment);
  if (language) params.set("language", language);
  if (stars) params.set("stars", String(stars));
  const data = useQuery({
    queryKey: ["reviews", params.toString()],
    queryFn: () => apiGet<AnyRec>(`/reviews?${params.toString()}`),
  });
  if (!data.data) return <Skeleton className="h-40" />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <label className="text-caption text-fg-3">
          Language
          <select className="ml-2 h-10 rounded-control border border-border px-2" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="">All</option>
            <option value="en">en</option>
            <option value="ar">ar</option>
            <option value="mixed">mixed</option>
          </select>
        </label>
        <label className="text-caption text-fg-3">
          Stars
          <select className="ml-2 h-10 rounded-control border border-border px-2" value={stars} onChange={(e) => setStars(e.target.value)}>
            <option value="">All</option>
            {[1, 2, 3, 4, 5].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-caption text-fg-3">
          Theme
          <input
            className="ml-2 h-10 rounded-control border border-border px-2 text-body"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            placeholder="theme slug"
          />
        </label>
        <a className="inline-flex h-10 items-center text-small text-fg-2" href={`http://localhost:8000/export.csv?company=${company}&${q}`}>
          Export CSV
        </a>
      </div>
      <p className="text-caption text-fg-3">{data.data.n} reviews</p>
      {(data.data.items ?? []).map((item: AnyRec) => (
        <div key={item.id} className="border-t border-divider pt-3">
          <p className="text-caption text-fg-3">
            {item.stars}★ · {item.date?.slice(0, 10)} · {item.store}
          </p>
          <ArabicText text={item.body} textEn={item.body_en} language={item.language} />
        </div>
      ))}
    </div>
  );
}

export function ThemeDetail({ data }: { data: AnyRec }) {
  return (
    <div className="space-y-4">
      {["a", "b"].map((side) => (
        <div key={side}>
          <h3 className="text-card">{data[side]?.label ?? side}</h3>
          {(data[side]?.snippets ?? []).map((sn: AnyRec, i: number) => (
            <ArabicText key={i} text={sn.text} textEn={sn.text_en} language={sn.language} />
          ))}
        </div>
      ))}
    </div>
  );
}
