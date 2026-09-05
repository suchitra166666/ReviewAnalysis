# Decisions

Checkpoint A confirmed 2026-09-05. Company IDs and live model prices are in `config/companies.yaml` and `config/models.yaml`.

## Settings cache fallback

`get_setting` loads `config/settings_defaults.yaml` into memory only when the database is unreachable (unit tests, pre-migrate). Runtime after a successful bootstrap still uses `app_settings`.

## CLI without a worker

If no worker heartbeat is younger than 15 seconds, `rap` runs the job inline so a local `rap scrape` works without `docker compose`. When a worker is alive, the CLI only queues and tails.

## DeepSeek estimate prices

Seed prices use DeepSeek **peak** rates so cost estimates stay conservative across peak/off-peak hours.

## OpenAI Sol price

Official short-context Standard rate on 2026-09-05 is $4 / $20 (promotional through 2026-11-21), not the spec draft $5 / $30.

## Hidden companies

Soft-delete is a `hidden` boolean on `companies`. Hidden rows stay in the database and drop out of selectors.

## Single dashboard (2026-09-05)

The Executive / Manager / Analyst view toggle is removed. There is one top-to-bottom dashboard. Exclude-flagged and weighting stay on in the API (`true`) and never appear as UI controls. URL state is companies + start/end dates only.

## Frontend API base

The Next.js app calls `http://localhost:8000` directly (CORS allow-list). This avoids a third `.env` variable. Docker publishes the API on that same host port.

## Worker heartbeat

`worker_heartbeat` is an extra table so `/health` can report worker liveness without Redis.
