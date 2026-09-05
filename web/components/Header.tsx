"use client";

import { Bookmark, Check, History, Plus, Settings } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Company } from "@/lib/api";
import { datesAreValid, laterLaunch } from "@/lib/dates";
import type { DashState } from "@/lib/url-state";
import { serializeState } from "@/lib/url-state";

export function Header({
  companies,
  state,
  setState,
  jobsRunning,
  nA,
  nB,
  dataAsOf,
  low,
  onUsableClick,
  sample,
  onSave,
  savedTitle,
  onNewReport,
}: {
  companies: Company[];
  state: DashState;
  setState: (next: DashState) => void;
  jobsRunning: number;
  nA?: number;
  nB?: number;
  dataAsOf?: string;
  low?: boolean;
  onUsableClick?: () => void;
  sample?: {
    n_a: number;
    n_b: number;
    usable_a: number;
    usable_b: number;
  } | null;
  /** Present once a report is on screen; opens the save dialog. */
  onSave?: () => void;
  /** Name of the saved copy being viewed or just saved, when there is one. */
  savedTitle?: string | null;
  /** Clears the current report and starts a fresh one. */
  onNewReport?: () => void;
}) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [dateError, setDateError] = useState("");
  const a = companies.find((c) => c.slug === state.a);
  const b = companies.find((c) => c.slug === state.b);
  const launch = laterLaunch(a, b);

  function push(next: DashState) {
    if (!datesAreValid(next.dateFrom, next.dateTo)) {
      setDateError("Start date must be before end date.");
      setState(next);
      return;
    }
    setDateError("");
    setState(next);
    router.replace(`/${serializeState(next)}`);
  }

  return (
    <header className="border-b border-border bg-bg">
      <div className="mx-auto max-w-page page-gutter py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <div className="flex min-w-0 flex-wrap items-baseline gap-3">
              <select
                aria-label="Company A"
                className="h-10 max-w-full min-w-0 rounded-control border border-border bg-bg px-2 text-display text-fg"
                value={state.a}
                onChange={(e) => push({ ...state, a: e.target.value })}
              >
                {companies.length === 0 ? <option value="">Choose company</option> : null}
                {companies.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.display_name}
                  </option>
                ))}
              </select>
              <span className="text-fg-3">vs</span>
              <select
                aria-label="Company B"
                className="h-10 max-w-full min-w-0 rounded-control border border-border bg-bg px-2 text-display text-fg"
                value={state.b}
                onChange={(e) => push({ ...state, b: e.target.value })}
              >
                {companies.length === 0 ? <option value="">Choose company</option> : null}
                {companies.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.display_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-caption text-fg-3">
                Start date
                <input
                  type="date"
                  aria-label="Start date"
                  className="ml-2 h-10 rounded-control border border-border bg-bg px-2 text-body text-fg"
                  value={state.dateFrom}
                  onChange={(e) => push({ ...state, dateFrom: e.target.value })}
                />
              </label>
              <label className="text-caption text-fg-3">
                End date
                <input
                  type="date"
                  aria-label="End date"
                  className="ml-2 h-10 rounded-control border border-border bg-bg px-2 text-body text-fg"
                  value={state.dateTo}
                  onChange={(e) => push({ ...state, dateTo: e.target.value })}
                />
              </label>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {onNewReport ? (
              <button
                type="button"
                onClick={onNewReport}
                className="inline-flex h-10 items-center gap-1.5 rounded-control border border-border px-3 text-small text-fg"
                aria-label="Start a new report"
              >
                <Plus size={16} strokeWidth={1.5} />
                <span className="hidden sm:inline">New report</span>
              </button>
            ) : null}
            {onSave ? (
              <button
                type="button"
                onClick={onSave}
                className={`inline-flex h-10 items-center gap-1.5 rounded-control border px-3 text-small ${
                  savedTitle ? "border-fg bg-fg text-bg" : "border-border text-fg"
                }`}
                aria-label={savedTitle ? `Saved as “${savedTitle}”. Rename or save again` : "Save this report"}
                title={savedTitle ? `Saved as “${savedTitle}”` : undefined}
              >
                {savedTitle ? <Check size={16} strokeWidth={1.5} /> : <Bookmark size={16} strokeWidth={1.5} />}
                <span className="hidden sm:inline">{savedTitle ? "Saved" : "Save report"}</span>
              </button>
            ) : null}
            <Link
              href="/history"
              className="inline-flex h-10 items-center gap-1.5 rounded-control px-2 text-small text-fg-2"
              aria-label="History of saved comparisons"
            >
              <History size={16} strokeWidth={1.5} />
              <span className="hidden sm:inline">History</span>
            </Link>
            <div className="relative">
              <button
                type="button"
                className="relative inline-flex h-10 w-10 items-center justify-center text-fg-3"
                aria-label="Settings"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((o) => !o)}
              >
                <Settings size={16} strokeWidth={1.5} />
                {jobsRunning > 0 ? (
                  <span className="absolute right-1 top-1 h-2 w-2 rounded-pill bg-a" aria-hidden />
                ) : null}
              </button>
              {menuOpen ? (
                <div className="absolute right-0 z-20 mt-1 w-48 rounded-control border border-border bg-bg py-1">
                  <Link href="/settings" className="block px-3 py-2 text-small text-fg" onClick={() => setMenuOpen(false)}>
                    Settings
                  </Link>
                  <Link href="/jobs" className="block px-3 py-2 text-small text-fg" onClick={() => setMenuOpen(false)}>
                    Jobs{jobsRunning > 0 ? ` · ${jobsRunning} jobs running` : ""}
                  </Link>
                  <Link href="/history" className="block px-3 py-2 text-small text-fg" onClick={() => setMenuOpen(false)}>
                    History
                  </Link>
                </div>
              ) : null}
            </div>
          </div>
        </div>
        {launch ? (
          <button
            type="button"
            className="mt-2 text-caption text-fg-2 underline"
            onClick={() => push({ ...state, dateFrom: launch.date })}
          >
            Set start to {launch.name}&apos;s launch ({launch.date})
          </button>
        ) : null}
        {dateError ? <p className="mt-2 text-caption text-bad">{dateError}</p> : null}
        <p className="mt-3 text-caption text-fg-3">
          {sample ? (
            <>
              Based on {sample.n_a.toLocaleString()} of {sample.usable_a.toLocaleString()} usable reviews for{" "}
              {a?.display_name ?? state.a} and {sample.n_b.toLocaleString()} of {sample.usable_b.toLocaleString()} for{" "}
              {b?.display_name ?? state.b} between {state.dateFrom} and {state.dateTo}.
            </>
          ) : (
            <>
              Based on {nA?.toLocaleString() ?? "—"} and {nB?.toLocaleString() ?? "—"}{" "}
              <button type="button" className="underline" onClick={onUsableClick}>
                usable
              </button>{" "}
              reviews between {state.dateFrom} and {state.dateTo}.
            </>
          )}{" "}
          Data as of {dataAsOf ? dataAsOf.slice(0, 10) : "—"}.
          {low ? <span className="ml-2 text-fg-2">Low confidence</span> : null}
        </p>
      </div>
    </header>
  );
}
