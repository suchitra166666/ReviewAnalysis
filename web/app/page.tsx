"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";
import { PipelineFlow } from "@/components/PipelineFlow";
import { Drawer, RunPipelineModal } from "@/components/RunPipelineModal";
import { SaveReportModal } from "@/components/SaveReportModal";
import {
  CompetitorSection,
  Explorer,
  IpaSection,
  JourneySection,
  KanoSection,
  KpiSection,
  MoreDetail,
  PainSection,
  PmSection,
  StarsSection,
  SummarySection,
  ThemeDetail,
  ThemeSection,
  TrendsSection,
} from "@/components/dashboard";
import Link from "next/link";
import { Button, Card, Skeleton } from "@/components/ui";
import { apiGet, type Company, type MetricDef, type SavedComparison, type SavedComparisonFull } from "@/lib/api";
import { formatStamp } from "@/lib/dates";
import { liveHref, parseSavedId, savedTitle } from "@/lib/history";
import { compareQuery, defaultState, parseState, serializeState, type DashState } from "@/lib/url-state";

type AnyRec = Record<string, any>;

function sortCompanies(rows: Company[]): Company[] {
  return [...rows].sort((x, y) => x.display_name.localeCompare(y.display_name));
}

export default function DashboardPage() {
  const router = useRouter();
  const [state, setState] = useState<DashState>(defaultState());
  const [ready, setReady] = useState(false);
  const [explorer, setExplorer] = useState<AnyRec | null>(null);
  const [theme, setTheme] = useState<string | null>(null);
  const [runOpen, setRunOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [regen, setRegen] = useState(0);
  // when set, the page shows a stored result from History instead of recomputing
  const [savedId, setSavedId] = useState<number | null>(null);
  // the copy the user just saved from this live view, so the header can say "Saved"
  const [justSaved, setJustSaved] = useState<SavedComparison | null>(null);

  useEffect(() => {
    setState(parseState(window.location.search));
    setSavedId(parseSavedId(window.location.search));
    setReady(true);
  }, []);

  const saved = useQuery({
    queryKey: ["saved", savedId],
    queryFn: () => apiGet<SavedComparisonFull>(`/history/${savedId}`),
    enabled: savedId != null,
    staleTime: Infinity,
  });
  const frozen = savedId != null;
  const snapshot = frozen ? saved.data?.snapshot : undefined;

  useEffect(() => {
    if (!saved.data || !frozen) return;
    setState({
      a: saved.data.a,
      b: saved.data.b,
      dateFrom: saved.data.date_from,
      dateTo: saved.data.date_to,
    });
  }, [saved.data, frozen]);

  /** Any change to companies or dates leaves the saved view and goes live. */
  function changeState(next: DashState) {
    setSavedId(null);
    setJustSaved(null);
    setState(next);
  }

  function goLive() {
    setSavedId(null);
    setJustSaved(null);
    router.replace(`/${serializeState(state)}`);
  }

  /** Leave whatever is on screen and start from the default companies and range. */
  function newReport() {
    setSavedId(null);
    setJustSaved(null);
    setState(defaultState());
    router.replace("/");
  }

  const setup = useQuery({
    queryKey: ["setup"],
    queryFn: () => apiGet<AnyRec>("/setup-status"),
  });
  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: () => apiGet<Company[]>("/companies"),
  });
  const glossary = useQuery({
    queryKey: ["glossary"],
    queryFn: () => apiGet<Record<string, MetricDef>>("/metrics-glossary"),
  });
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: () => apiGet<AnyRec[]>("/jobs"),
    refetchInterval: 2000,
  });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<AnyRec>("/health"),
    refetchInterval: 5000,
  });

  const listed = sortCompanies(companies.data ?? []);

  useEffect(() => {
    if (setup.data && !setup.data.ready) router.replace("/setup");
  }, [setup.data, router]);

  useEffect(() => {
    if (!listed.length || !ready || frozen) return;
    if (!state.a || !state.b) {
      const next = {
        ...state,
        a: state.a || listed[0].slug,
        b: state.b || listed[1]?.slug || listed[0].slug,
      };
      setState(next);
      router.replace(`/${serializeState(next)}`);
    }
  }, [listed, ready, router, state, frozen]);

  const q = useMemo(() => (state.a && state.b ? compareQuery(state) : ""), [state]);
  const live = Boolean(q) && !frozen;
  const compare = useQuery({
    queryKey: ["compare", q],
    queryFn: () => apiGet<AnyRec>(`/compare?${q}`),
    enabled: live,
  });
  const journey = useQuery({
    queryKey: ["journey", q],
    queryFn: () => apiGet<AnyRec>(`/frameworks/journey?${q}`),
    enabled: live,
  });
  const kano = useQuery({
    queryKey: ["kano", q],
    queryFn: () => apiGet<AnyRec>(`/frameworks/kano?${q}`),
    enabled: live,
  });
  const ipa = useQuery({
    queryKey: ["ipa", q],
    queryFn: () => apiGet<AnyRec>(`/frameworks/ipa?${q}`),
    enabled: live,
  });
  const summary = useQuery({
    queryKey: ["summary", q, regen],
    queryFn: () => apiGet<AnyRec>(`/summary?${q}${regen ? "&regenerate=true" : ""}`),
    enabled: live,
  });
  const themeData = useQuery({
    queryKey: ["theme", theme, q],
    queryFn: () => apiGet<AnyRec>(`/theme/${theme}?${q}`),
    enabled: Boolean(theme && q),
  });

  // one view model for both modes: stored snapshot or live queries
  const view = frozen
    ? {
        compare: snapshot?.compare as AnyRec | undefined,
        summary: (snapshot?.summary ?? undefined) as AnyRec | undefined,
        journey: snapshot?.journey as AnyRec | undefined,
        kano: snapshot?.kano as AnyRec | undefined,
        ipa: snapshot?.ipa as AnyRec | undefined,
        loading: saved.isLoading,
        error: saved.isError,
        summaryLoading: false,
        journeyLoading: false,
        kanoLoading: false,
        ipaLoading: false,
      }
    : {
        compare: compare.data,
        summary: summary.data,
        journey: journey.data,
        kano: kano.data,
        ipa: ipa.data,
        loading: Boolean(q) && compare.isLoading,
        error: compare.isError,
        summaryLoading: summary.isLoading,
        journeyLoading: journey.isLoading,
        kanoLoading: kano.isLoading,
        ipaLoading: ipa.isLoading,
      };

  const g = glossary.data ?? {};
  const oa = view.compare?.a?.overview;
  const ob = view.compare?.b?.overview;
  const low = Boolean(oa?.meta?.low_confidence || ob?.meta?.low_confidence);
  const pairJobs = (jobs.data ?? []).filter((j) => {
    const slugs = j.params?.slugs ?? [j.params?.a, j.params?.b];
    return slugs?.includes(state.a) && slugs?.includes(state.b);
  });
  const activeJobs = pairJobs.filter((j) => j.status === "running" || j.status === "queued");
  const running = (jobs.data ?? []).filter((j) => j.status === "running" || j.status === "queued").length;
  const latestJob = activeJobs[0] ?? pairJobs[0];
  const workerOk = health.data?.worker === "ok";
  const nameA = listed.find((c) => c.slug === state.a)?.display_name ?? state.a;
  const nameB = listed.find((c) => c.slug === state.b)?.display_name ?? state.b;
  const scraped = (oa?.reviews_scraped ?? 0) + (ob?.reviews_scraped ?? 0);
  const analysed = (oa?.reviews_analysed ?? 0) + (ob?.reviews_analysed ?? 0);
  const noAnalysed = Boolean(view.compare && analysed === 0);
  const scrapedOnly = noAnalysed && scraped > 0;

  function openExplorer(extra: AnyRec) {
    setExplorer({ company: state.a, ...extra });
  }

  function openMore() {
    setMoreOpen(true);
    requestAnimationFrame(() => document.getElementById("more-detail")?.scrollIntoView({ behavior: "smooth" }));
  }

  return (
    <div>
      <Header
        companies={listed}
        state={state}
        setState={changeState}
        jobsRunning={running}
        nA={oa?.meta?.n_used}
        nB={ob?.meta?.n_used}
        dataAsOf={oa?.meta?.data_as_of}
        low={low}
        onUsableClick={openMore}
        sample={view.compare?.sample?.used ? view.compare.sample : null}
        onSave={view.compare && !noAnalysed ? () => setSaveOpen(true) : undefined}
        savedTitle={frozen && saved.data ? savedTitle(saved.data) : justSaved ? savedTitle(justSaved) : null}
        onNewReport={newReport}
      />
      <main className="mx-auto max-w-page space-y-12 page-gutter py-8">
        {setup.isError || companies.isError ? (
          <Card>
            <p className="text-body">The API is not reachable. Start the stack, then refresh.</p>
          </Card>
        ) : null}

        {frozen && saved.data ? (
          <Card low>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-card">Saved result · {savedTitle(saved.data)}</p>
                <p className="mt-1 text-caption text-fg-3">
                  Captured {formatStamp(saved.data.created_at)}. This is the comparison exactly as it was then; review
                  drill-downs open current data.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button onClick={newReport}>New report</Button>
                <Link href={liveHref(saved.data)} className="inline-flex h-10 items-center rounded-control border border-border px-3 text-small text-fg" onClick={() => setSavedId(null)}>
                  Open with current data
                </Link>
                <Link href="/history" className="inline-flex h-10 items-center px-2 text-small text-fg-2">
                  All saved comparisons
                </Link>
              </div>
            </div>
          </Card>
        ) : null}

        {frozen && saved.isError ? (
          <Card>
            <p className="text-body">This saved comparison no longer exists.</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link href="/history" className="inline-flex h-10 items-center text-small text-fg-2">
                Open History
              </Link>
              <button type="button" className="inline-flex h-10 items-center text-small text-fg-2 underline" onClick={goLive}>
                Show current data instead
              </button>
            </div>
          </Card>
        ) : null}

        {listed.length === 0 && companies.isSuccess ? (
          <Card>
            <p className="text-body">Choose two companies to compare.</p>
          </Card>
        ) : null}

        {listed.length > 0 && (!state.a || !state.b) && !frozen ? (
          <Card>
            <p className="text-body">Choose two companies to compare.</p>
          </Card>
        ) : null}

        {view.loading ? (
          <div className="grid gap-6 md:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-40" />
            ))}
          </div>
        ) : null}

        {view.error && !frozen ? (
          <Card>
            <p className="text-body">The comparison could not be loaded. Check that the API is running and two companies are selected.</p>
          </Card>
        ) : null}

        {!frozen && (noAnalysed || activeJobs.length > 0) ? (
          <Card>
            <h2 className="text-section">Processing flow</h2>
            <p className="mt-1 text-caption text-fg-3">
              {latestJob
                ? `Job #${latestJob.id} · ${latestJob.status}`
                : "Seven stages from scrape to summarise. Run the pipeline to start."}
            </p>
            <div className="mt-6">
              <PipelineFlow job={latestJob} />
            </div>
            {noAnalysed ? (
              <p className="mt-6 text-body">
                {scrapedOnly
                  ? "Reviews are scraped but not yet analysed."
                  : `No analysed reviews for ${nameA} or ${nameB} in this range.`}
              </p>
            ) : (
              <p className="mt-6 text-body">A job is running. Sections below will update when it finishes.</p>
            )}
            {latestJob?.status === "queued" && !workerOk ? (
              <p className="mt-3 text-small text-fg-2">
                The worker is not running. Start it with rap worker or docker compose up.
              </p>
            ) : null}
            {noAnalysed ? (
              <div className="mt-4 flex flex-wrap gap-2">
                <Button onClick={() => setRunOpen(true)}>Run pipeline for these companies</Button>
                <Link href="/jobs" className="inline-flex h-10 items-center text-small text-fg-2">
                  Open Jobs
                </Link>
              </div>
            ) : (
              <Link href="/jobs" className="mt-4 inline-flex h-10 items-center text-small text-fg-2">
                Open Jobs
              </Link>
            )}
          </Card>
        ) : null}

        {view.compare && !noAnalysed ? (
          <>
            <SummarySection
              summary={view.summary}
              watch={view.summary?.watch_list ?? view.compare.a.watch_list ?? []}
              loading={view.summaryLoading}
              onTheme={setTheme}
            />
            <KpiSection a={view.compare.a} b={view.compare.b} deltas={view.compare.deltas ?? []} glossary={g} onExplore={openExplorer} />
            <StarsSection a={view.compare.a} b={view.compare.b} />
            <PainSection
              a={view.compare.a}
              b={view.compare.b}
              glossary={g}
              onTheme={setTheme}
              explanations={view.summary?.pain_point_explanations}
            />
            <JourneySection
              data={view.journey}
              glossary={g}
              onTheme={setTheme}
              loading={view.journeyLoading}
              reads={view.summary?.journey_read}
              nameA={nameA}
              nameB={nameB}
            />
            <KanoSection data={view.kano} glossary={g} loading={view.kanoLoading} nameA={nameA} nameB={nameB} />
            <ThemeSection a={view.compare.a} b={view.compare.b} glossary={g} onTheme={setTheme} />
            <IpaSection data={view.ipa} onTheme={setTheme} glossary={g} loading={view.ipaLoading} nameA={nameA} nameB={nameB} />
            <TrendsSection a={view.compare.a} b={view.compare.b} glossary={g} />
            <CompetitorSection a={view.compare.a} b={view.compare.b} glossary={g} />
            <PmSection
              summary={view.summary}
              loading={view.summaryLoading}
              nameA={nameA}
              nameB={nameB}
              onTheme={setTheme}
              onRegen={() => {
                if (frozen) goLive();
                setRegen((n) => n + 1);
              }}
            />
            <MoreDetail
              a={view.compare.a}
              b={view.compare.b}
              glossary={g}
              stateA={state.a}
              q={q}
              onExplore={openExplorer}
              open={moreOpen}
              setOpen={setMoreOpen}
            />
          </>
        ) : null}
      </main>

      {explorer ? (
        <Drawer title="Review explorer" onClose={() => setExplorer(null)}>
          <Explorer company={explorer.company ?? state.a} extra={explorer} q={q} />
        </Drawer>
      ) : null}
      {theme ? (
        <Drawer title={theme.replace(/_/g, " ")} onClose={() => setTheme(null)}>
          {themeData.data ? <ThemeDetail data={themeData.data} /> : <Skeleton className="h-40" />}
        </Drawer>
      ) : null}
      {saveOpen ? (
        <Drawer title="Save report" onClose={() => setSaveOpen(false)}>
          <SaveReportModal
            state={state}
            nameA={nameA}
            nameB={nameB}
            existingTitle={frozen && saved.data ? saved.data.title : justSaved?.title}
            onSaved={setJustSaved}
            onClose={() => setSaveOpen(false)}
          />
        </Drawer>
      ) : null}
      {runOpen ? (
        <Drawer title="Run pipeline" onClose={() => setRunOpen(false)}>
          <RunPipelineModal state={state} companies={listed} onClose={() => setRunOpen(false)} />
        </Drawer>
      ) : null}
    </div>
  );
}
