# Build log

## Checkpoint A (2026-09-05)

Confirmed company IDs and verified model prices. Seed files written from that table.

## Phase 1 — Scaffold, DB, scraper

Built: docker-compose (Postgres 16 + pgvector, api, worker, web), `make init` / `make migrate`, Alembic `001_initial` for every specified table plus `hidden` on companies and `worker_heartbeat`, encrypted settings store, job queue + worker, Play/App Store scrapers with RSS fallback, CLI that shares the job path.

Verified: unit tests for fixture parsing, dedupe, incremental stop (no network).

Uncertain: live scrape smoke (`rap scrape --company keeta --store all --full`) needs Docker Postgres and store availability; not run in this pass.

## Phase 2 — Extraction A

Built: Pydantic extraction schema, `extract_v3.md`, `rap/llm/client.py` (structured outputs when the provider supports them), batching, retry-once then `schema_valid=false`, alias resolution, `--dry-run`.

Verified: schema validation, batching, alias tests.

Uncertain: Checkpoint B (10 rows next to raw text) needs a real key and scraped reviews. Not spent.

## Phase 3 — Extraction B, reconcile, translate

Built: DeepSeek path (`json_object`, thinking disabled), reconcile rules (neutral/mixed agree; sub-theme/snippet ignored), tiebreak call, idempotent translate.

Verified: synthetic reconcile pairs.

Uncertain: live agreement rate (Checkpoint D) not measured.

## Phase 4 — Flags

Built: embeddings batch 100, near-duplicate cosine, burst flag, incentivized score, exclusion reasons. Rows are never deleted.

Verified: cosine unit test.

## Phase 5 — Aggregation and API

Built: post-stratification weights, Wilson + difference CI, Pareto, momentum, journey/Kano/IPA, compare + summary cache, FastAPI routes for analysis, settings, jobs, health. Settings never return a raw key.

Verified: weights, Wilson, Pareto, IPA quadrants.

## Phase 6 — Dashboard

Built: Next.js 14 App Router dashboard with MetricLabel, Arabic+EN rendering, Settings, Jobs, first-run `/setup`, URL state, design tokens, Vitest for delta colour, URL state, key masking, and MetricLabel lint.

Verified: Python unit tests (see below). Browser screenshots at 1440/1024/390 and Playwright wizard flow still need a running stack and are listed as remaining verification.

Uncertain: live LLM spend is $0 until keys are entered and a job is confirmed (Checkpoint C).

## UI correction (2026-09-05)

Removed Executive / Manager / Analyst toggle and all per-role hiding. Header is now Company A, vs, Company B, start/end dates, and a gear menu (Settings / Jobs). Exclude-flagged and weighted stay on in the API and are never shown. Run pipeline lives on Jobs, plus the no-data empty state. Empty states cover API down, no selection, no analysed reviews, and scraped-but-not-extracted. More detail is a single collapsed section at the bottom.
