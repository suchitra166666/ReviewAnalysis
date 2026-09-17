"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Button, Input } from "@/components/ui";
import { apiGet, apiSend, type Company } from "@/lib/api";
import { PIPELINE_STAGES } from "@/lib/pipeline";
import type { DashState } from "@/lib/url-state";

const ALL_STAGES = [...PIPELINE_STAGES];
const PRESETS = [100, 500, 1000] as const;

type AnyRec = Record<string, any>;

export function RunPipelineModal({
  state,
  companies,
  onClose,
}: {
  state: DashState;
  companies: Company[];
  onClose: () => void;
}) {
  const [slugs, setSlugs] = useState<string[]>([state.a, state.b].filter(Boolean));
  const [from, setFrom] = useState(state.dateFrom);
  const [to, setTo] = useState(state.dateTo);
  const [stages, setStages] = useState<string[]>(ALL_STAGES);
  const [sampleN, setSampleN] = useState<number | "all">(100);
  const [custom, setCustom] = useState("100");
  const [estimate, setEstimate] = useState<AnyRec | null>(null);
  const [error, setError] = useState("");
  const setup = useQuery({
    queryKey: ["setup"],
    queryFn: () => apiGet<{ has_own_key?: boolean }>("/setup-status"),
  });
  const hasKey = Boolean(setup.data?.has_own_key);

  function params() {
    const n = sampleN === "all" ? null : Math.max(1, Math.floor(Number(sampleN) || 0));
    return {
      slugs,
      a: slugs[0],
      b: slugs[1],
      stores: ["appstore", "play"],
      date_from: from,
      date_to: to,
      stages,
      ...(n
        ? { sample_n: n, sample_per_star: Math.max(1, Math.floor(n / 5)) }
        : {}),
    };
  }

  useEffect(() => {
    let cancelled = false;
    const handle = setTimeout(async () => {
      setError("");
      try {
        const out = await apiSend<AnyRec>("/jobs/estimate", "POST", { kind: "full_pipeline", params: params() });
        if (!cancelled) setEstimate(out);
      } catch (err) {
        if (!cancelled) setError(String(err));
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slugs.join(","), from, to, stages.join(","), sampleN]);

  async function run(confirm: boolean) {
    setError("");
    if (!hasKey) {
      setError("Add your OpenAI or DeepSeek key to run a report.");
      return;
    }
    try {
      await apiSend("/jobs", "POST", { kind: "full_pipeline", confirm, params: params() });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the report.");
    }
  }

  const breakdown = estimate?.breakdown ?? {};

  return (
    <div className="space-y-4">
      <p className="text-body">Pick companies, the date range, how many reviews to analyse, and stages.</p>
      <div className="grid gap-2">
        {companies.map((c) => (
          <label key={c.slug} className="inline-flex h-10 items-center gap-2 text-small">
            <input
              type="checkbox"
              checked={slugs.includes(c.slug)}
              onChange={(e) =>
                setSlugs((prev) => (e.target.checked ? [...prev, c.slug] : prev.filter((s) => s !== c.slug)))
              }
            />
            {c.display_name}
          </label>
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        <label className="text-caption text-fg-3">
          Start
          <input
            type="date"
            className="ml-2 h-10 rounded-control border border-border px-2 text-body"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </label>
        <label className="text-caption text-fg-3">
          End
          <input
            type="date"
            className="ml-2 h-10 rounded-control border border-border px-2 text-body"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </label>
      </div>
      <fieldset className="space-y-2">
        <legend className="text-caption text-fg-3">Reviews to analyse per company</legend>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((n) => (
            <Button
              key={n}
              variant={sampleN === n ? "primary" : "ghost"}
              onClick={() => {
                setSampleN(n);
                setCustom(String(n));
              }}
            >
              {n.toLocaleString()}
            </Button>
          ))}
          <Button
            variant={sampleN === "all" ? "primary" : "ghost"}
            onClick={() => {
              setSampleN("all");
              setCustom("");
            }}
          >
            All
          </Button>
        </div>
        <label className="block text-caption text-fg-3">
          Custom number
          <Input
            className="mt-1"
            inputMode="numeric"
            value={custom}
            onChange={(e) => {
              const raw = e.target.value;
              setCustom(raw);
              const n = parseInt(raw, 10);
              if (Number.isFinite(n) && n > 0) setSampleN(n);
            }}
          />
        </label>
        {sampleN !== "all" ? (
          <p className="text-caption text-fg-3">
            Star-balanced sample: {Math.max(1, Math.floor(Number(sampleN) / 5))} reviews per star. Scrape still stores every review.
          </p>
        ) : null}
      </fieldset>
      <div className="flex flex-wrap gap-3">
        {ALL_STAGES.map((stage) => (
          <label key={stage} className="inline-flex h-10 items-center gap-2 text-small">
            <input
              type="checkbox"
              checked={stages.includes(stage)}
              onChange={(e) =>
                setStages((prev) => (e.target.checked ? [...prev, stage] : prev.filter((s) => s !== stage)))
              }
            />
            {stage.replace(/_/g, " ")}
          </label>
        ))}
      </div>
      {estimate ? (
        <div className="space-y-1 text-small">
          <p>Estimated ${Number(estimate.est_cost_usd || 0).toFixed(2)}</p>
          <ul className="text-caption text-fg-2">
            <li>Extract A ${Number(breakdown.extract_a || 0).toFixed(2)}</li>
            <li>Extract B ${Number(breakdown.extract_b || 0).toFixed(2)}</li>
            <li>Tiebreak ${Number(breakdown.tiebreak || 0).toFixed(2)}</li>
            <li>Translate ${Number(breakdown.translate || 0).toFixed(2)}</li>
            <li>Summarise ${Number(breakdown.summarise || 0).toFixed(2)}</li>
          </ul>
          {estimate.refused ? <p className="text-bad">Above the cap of ${estimate.cap}</p> : null}
        </div>
      ) : (
        <p className="text-caption text-fg-3">Estimating…</p>
      )}
      {!hasKey ? (
        <p className="text-small text-fg">
          Add your OpenAI or DeepSeek key first.{" "}
          <Link href="/settings" className="underline" onClick={onClose}>
            Open Settings
          </Link>
        </p>
      ) : null}
      {estimate?.requires_confirmation && !estimate.refused ? (
        <Button onClick={() => run(true)} disabled={!hasKey}>
          Confirm and run
        </Button>
      ) : (
        <Button onClick={() => run(false)} disabled={!hasKey || Boolean(estimate?.refused) || !estimate}>
          Run pipeline
        </Button>
      )}
      {error ? <p className="text-small text-bad">{error}</p> : null}
    </div>
  );
}

export function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-30 flex justify-end bg-fg/20">
      <div className="h-full w-full max-w-xl overflow-y-auto bg-bg p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-section">{title}</h2>
          <Button variant="ghost" onClick={onClose} aria-label="Close">
            Close
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}
