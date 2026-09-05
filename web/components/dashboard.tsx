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

export function StarsSection({ a, b }: { a: AnyRec; b: AnyRec }) {
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
        metricKey="reviews_analysed"
        glossary={{}}
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
  return (
    <SectionFrame title="Pain points and strengths" empty={empty ? "No pain points or strengths in this range." : undefined}>
      <div className="grid gap-6 md:grid-cols-2">
        <PainCol company={a.overview.meta.company_name} rows={a.pain_points} color="a" glossary={glossary} onTheme={onTheme} explanations={explanations} />
        <PainCol company={b.overview.meta.company_name} rows={b.pain_points} color="b" glossary={glossary} onTheme={onTheme} explanations={explanations} />
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <StrengthCol company={a.overview.meta.company_name} rows={a.strengths} color="a" onTheme={onTheme} />
        <StrengthCol company={b.overview.meta.company_name} rows={b.strengths} color="b" onTheme={onTheme} />
      </div>
    </SectionFrame>
  );
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

function PainCol({ company, rows, color, glossary, onTheme, explanations }: AnyRec) {
  return (
    <Card className={color === "a" ? "border-l-[3px] border-l-a" : "border-l-[3px] border-l-b"}>
      <h3 className="text-card">{company}</h3>
      <MetricLabel metricKey="severity" glossary={glossary} />
      <div className="mt-3 space-y-4">
        {(rows ?? []).map((row: AnyRec) => (
          <button key={row.theme} type="button" className="block w-full text-left" onClick={() => onTheme(row.theme)}>
            <p className="text-small text-fg">{row.label}</p>
            <p className="text-caption text-fg-2">
              {formatPct(row.negative_rate)} · star drag {row.star_drag?.toFixed?.(1)}★
              {row.kano ? ` · ${String(row.kano).replace("_", "-")}` : ""}
              {row.journey_stage ? ` · ${String(row.journey_stage).replace(/_/g, " ")}` : ""}
            </p>
            <p className="text-caption">{explanationFor(row, explanations)}</p>
            {(row.snippets ?? []).slice(0, 2).map((sn: AnyRec, i: number) => (
              <ArabicText key={i} text={sn.text} textEn={sn.text_en} language={sn.language} />
            ))}
          </button>
        ))}
      </div>
    </Card>
  );
}

function StrengthCol({ company, rows, color, onTheme }: AnyRec) {
  return (
    <Card className={color === "a" ? "border-l-[3px] border-l-a" : "border-l-[3px] border-l-b"}>
      <h3 className="text-card">{company} · strengths</h3>
      <div className="mt-3 space-y-2">
        {(rows ?? []).map((row: AnyRec) => (
          <button key={row.theme} type="button" className="block w-full text-left text-small" onClick={() => onTheme(row.theme)}>
            {row.label} · {formatPct(row.positive_rate ?? row.negative_rate)}
          </button>
        ))}
        {!(rows ?? []).length ? <p className="text-caption text-fg-3">No strengths in this range.</p> : null}
      </div>
    </Card>
  );
}

export function JourneySection({ data, glossary, onTheme, loading, reads, nameA = "A", nameB = "B" }: AnyRec) {
  const names: Record<string, string> = { a: nameA, b: nameB };
  const labels: Record<string, string> = {
    discover_browse: "Discover",
    order_checkout: "Order",
    wait_track: "Wait",
    receive: "Receive",
    recover_support: "Recover",
  };
  const order = ["discover_browse", "order_checkout", "wait_track", "receive", "recover_support"];
  return (
    <SectionFrame title="Where the experience breaks" loading={loading} empty={!data && !loading ? "Journey map is not available yet." : undefined}>
      {data ? (
        <>
          <CompanyLegend nameA={nameA} nameB={nameB} sides={false} note="One row per company, stages Discover → Order → Wait → Receive → Recover." />
          <MetricLabel metricKey="negative_pct" glossary={glossary} />
          {["a", "b"].map((side) => (
            <div key={side}>
              <p className={`mb-2 text-caption font-medium ${side === "a" ? "text-a" : "text-b"}`}>{names[side]}</p>
              <div className="grid gap-2 md:grid-cols-5">
              {(data[side]?.cells ?? []).map((cell: AnyRec) => (
                <button
                  key={cell.stage}
                  type="button"
                  onClick={() => cell.top_theme && onTheme(cell.top_theme)}
                  className={`rounded-card border p-4 text-left ${cell.stage === data[side].peak_stage ? "border-fg" : "border-border"} ${side === "a" ? "border-l-[3px] border-l-a" : "border-l-[3px] border-l-b"}`}
                >
                  <p className="text-caption text-fg-3">{labels[cell.stage]}</p>
                  <p className="text-card">{formatPct(cell.negative_rate)}</p>
                  <p className="text-caption text-fg-2">{formatPct(cell.complaint_share)} of complaints</p>
                  <p className="text-caption">{(cell.top_theme ?? "").replace(/_/g, " ")}</p>
                  {cell.snippet ? <ArabicText text={cell.snippet.text} textEn={cell.snippet.text_en} language={cell.snippet.language} /> : null}
                </button>
              ))}
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
  const rows = a.theme_matrix ?? [];
  const byB = Object.fromEntries((b.theme_matrix ?? []).map((r: AnyRec) => [r.theme, r]));
  const radar = rows.map((row: AnyRec) => ({
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
        <div className="h-72">
          <ResponsiveContainer>
            <RadarChart data={radar}>
              <PolarGrid stroke="var(--divider)" />
              <PolarAngleAxis dataKey="theme" tick={{ fontSize: 12, fill: "var(--fg-3)" }} />
              <PolarRadiusAxis tick={{ fontSize: 12, fill: "var(--fg-3)" }} />
              <Radar dataKey="a" name={nameA} stroke="var(--a)" fill="var(--a)" fillOpacity={0.15} />
              <Radar dataKey="b" name={nameB} stroke="var(--b)" fill="var(--b)" fillOpacity={0.15} />
              <Legend wrapperStyle={{ fontSize: 12, color: "var(--fg-2)" }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
        <p>
          <a href="#theme-table" className="text-caption text-fg-3">
            View as table
          </a>
        </p>
      </Card>
      <Card>
        <p className="mb-2 text-caption text-fg-3">
          <MetricLabel metricKey="negative_pct" glossary={glossary} /> for each theme, per company
        </p>
        <table id="theme-table" className="w-full text-left">
          <thead className="text-caption text-fg-3">
            <tr className="h-11">
              <th className="px-3">Theme</th>
              <th className="px-3 text-right text-a">{nameA}</th>
              <th className="px-3 text-right text-b">{nameB}</th>
              <th className="px-3">Stage</th>
              <th className="px-3">Kano</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: AnyRec) => (
              <tr key={row.theme} className="h-11 cursor-pointer border-t border-divider" onClick={() => onTheme(row.theme)}>
                <td className="px-3 text-small">{row.label}</td>
                <td className="px-3 text-right text-small">{formatPct(row.negative_rate)}</td>
                <td className="px-3 text-right text-small">{formatPct(byB[row.theme]?.negative_rate)}</td>
                <td className="px-3 text-caption">{row.journey_stage}</td>
                <td className="px-3 text-caption">{row.kano}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </section>
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

export function TrendsSection({ a, b, glossary }: { a: AnyRec; b: AnyRec; glossary: Glossary }) {
  const [norm, setNorm] = useState(false);
  const seriesA = a.trends?.series ?? [];
  const seriesB = b.trends?.series ?? [];
  const weeks = Array.from(new Set([...seriesA.map((s: AnyRec) => s.week), ...seriesB.map((s: AnyRec) => s.week)])).sort();
  const meanA = seriesA.length ? seriesA.reduce((s: number, x: AnyRec) => s + (x.volume || 0), 0) / seriesA.length : 1;
  const meanB = seriesB.length ? seriesB.reduce((s: number, x: AnyRec) => s + (x.volume || 0), 0) / seriesB.length : 1;
  const byA = Object.fromEntries(seriesA.map((s: AnyRec) => [s.week, s]));
  const byB = Object.fromEntries(seriesB.map((s: AnyRec) => [s.week, s]));
  const chart = weeks.map((week) => ({
    week,
    aNeg: (byA[week]?.negative_pct ?? 0) * 100,
    bNeg: (byB[week]?.negative_pct ?? 0) * 100,
    aRate: byA[week]?.rating,
    bRate: byB[week]?.rating,
    aVol: norm ? (byA[week]?.volume ?? 0) / meanA : byA[week]?.volume ?? 0,
    bVol: norm ? (byB[week]?.volume ?? 0) / meanB : byB[week]?.volume ?? 0,
  }));
  if (!weeks.length) return <SectionFrame title="Trends" empty="No trend series in this range.">{null}</SectionFrame>;
  const nameA = a.overview?.meta?.company_name ?? "A";
  const nameB = b.overview?.meta?.company_name ?? "B";
  const legendStyle = { fontSize: 12, color: "var(--fg-2)" };
  const tickStyle = { fontSize: 12, fill: "var(--fg-3)" };
  const seriesLabel = (key: string) =>
    key === "aNeg" ? `${nameA} negative %` : key === "bNeg" ? `${nameB} negative %` : key === "aRate" ? `${nameA} rating` : key === "bRate" ? `${nameB} rating` : key === "aVol" ? `${nameA} reviews/week` : key === "bVol" ? `${nameB} reviews/week` : key;
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-section">Trends</h2>
        <CompanyLegend nameA={nameA} nameB={nameB} sides={false} note="Solid line is negative %, faint line is analysed rating, by week." />
      </div>
      <Card>
        <p className="mb-2 text-caption text-fg-3">Negative % and analysed rating</p>
        <div className="h-64">
          <ResponsiveContainer>
            <LineChart data={chart}>
              <XAxis dataKey="week" tick={tickStyle} />
              <YAxis tick={tickStyle} />
              <Tooltip formatter={(value: any, key: any) => [typeof value === "number" ? value.toFixed(1) : value, seriesLabel(String(key))]} />
              <Legend wrapperStyle={legendStyle} iconType="plainline" />
              <Line type="monotone" dataKey="aNeg" name={seriesLabel("aNeg")} stroke="var(--a)" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="bNeg" name={seriesLabel("bNeg")} stroke="var(--b)" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="aRate" name={seriesLabel("aRate")} stroke="var(--a)" strokeOpacity={0.4} strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="bRate" name={seriesLabel("bRate")} stroke="var(--b)" strokeOpacity={0.4} strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <p className="mb-1 text-caption font-medium text-a">{nameA}</p>
          <MetricLabel metricKey="momentum" glossary={glossary} />
          <p className="text-kpi">{formatPct(a.trends?.momentum?.negative_pct)}</p>
        </Card>
        <Card>
          <p className="mb-1 text-caption font-medium text-a">{nameA}</p>
          <MetricLabel metricKey="net_sentiment" glossary={glossary} />
          <p className="text-kpi">{formatPct(a.trends?.momentum?.net_sentiment)}</p>
        </Card>
        <Card>
          <p className="mb-1 text-caption font-medium text-a">{nameA}</p>
          <MetricLabel metricKey="share_of_voice" glossary={glossary} />
          <p className="text-small text-fg-2">Volume change {a.trends?.momentum?.volume}</p>
        </Card>
      </div>
      <Card>
        <div className="mb-2 flex items-center justify-between">
          <MetricLabel metricKey="share_of_voice" glossary={glossary} />
          <button type="button" className="text-small text-fg-2" onClick={() => setNorm((v) => !v)}>
            {norm ? "Normalised" : "Raw"}
          </button>
        </div>
        <div className="h-48">
          <ResponsiveContainer>
            <LineChart data={chart}>
              <XAxis dataKey="week" tick={tickStyle} />
              <YAxis tick={tickStyle} />
              <Tooltip formatter={(value: any, key: any) => [typeof value === "number" ? value.toFixed(norm ? 2 : 0) : value, seriesLabel(String(key))]} />
              <Legend wrapperStyle={legendStyle} iconType="plainline" />
              <Line type="monotone" dataKey="aVol" name={seriesLabel("aVol")} stroke="var(--a)" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="bVol" name={seriesLabel("bVol")} stroke="var(--b)" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </section>
  );
}

export function CompetitorSection({ a, b, glossary }: { a: AnyRec; b: AnyRec; glossary: Glossary }) {
  return (
    <section className="space-y-4">
      <h2 className="text-section">Competitor pull and churn</h2>
      <div className="grid gap-6 md:grid-cols-2">
        {[a, b].map((side: AnyRec, i: number) => (
          <Card key={side.overview.meta.company_slug} className={`space-y-3 border-l-[3px] ${i === 0 ? "border-l-a" : "border-l-b"}`}>
            <h3 className={`text-card ${i === 0 ? "text-a" : "text-b"}`}>{side.overview.meta.company_name}</h3>
            <MetricLabel metricKey="churn_signal" glossary={glossary} n={side.overview.meta.n_used} />
            <p className="text-kpi">{formatPct(side.overview.churn_signal?.value)}</p>
            <MetricLabel metricKey="competitor_pull" glossary={glossary} />
            {Object.keys(side.competitor_pull?.outbound ?? {}).length === 0 ? (
              <p className="text-caption text-fg-3">No competitor mentions in this range.</p>
            ) : (
              Object.entries(side.competitor_pull.outbound).map(([slug, counts]: any) => (
                <p key={slug} className="text-small">
                  {slug}: better {counts.competitor_better ?? 0} · worse {counts.competitor_worse ?? 0} · neutral {counts.neutral ?? 0}
                </p>
              ))
            )}
            <p className="text-caption text-fg-3">What other companies&apos; users say about this company</p>
            {Object.entries(side.competitor_pull?.inbound ?? {}).map(([slug, counts]: any) => (
              <p key={slug} className="text-small">
                {slug}: better {counts.competitor_better ?? 0} · worse {counts.competitor_worse ?? 0} · neutral {counts.neutral ?? 0}
              </p>
            ))}
            {((side.competitor_pull?.snippets ? Object.values(side.competitor_pull.snippets).flat() : []) as AnyRec[])
              .slice(0, 3)
              .map((sn, i) => (
                <ArabicText key={i} text={sn.text} textEn={sn.text_en} language={sn.language} />
              ))}
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
          <p className="text-small text-fg-2">{summary.competitor_pull_read}</p>
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
