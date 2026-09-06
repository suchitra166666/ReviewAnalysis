# Review Analysis Platform (RAP)

Self-hosted tool for product managers at food-delivery companies. It scrapes public App Store and Google Play reviews, labels them with two independent LLMs against a fixed theme taxonomy, and presents a two-company comparison dashboard.

**Live:** [https://web-production-f02c6.up.railway.app](https://web-production-f02c6.up.railway.app)

## 5-minute quickstart

```bash
git clone https://github.com/suchitra166666/ReviewAnalysis.git
cd ReviewAnalysis
make init
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). Follow the first-run wizard: paste at least one API key, test it, confirm model roles and the cost cap, keep or edit the seeded companies, then run the first scrape.

`.env` contains only two values, both generated or filled by `make init`:

```
DATABASE_URL=postgresql+psycopg://rap:rap@localhost:5432/rap
SETTINGS_ENCRYPTION_KEY=<fernet-key>
```

Keys, models, thresholds, and companies are edited in the web Settings screen after that. Editing YAML files after the first run does nothing unless you click Reset to defaults.

## Deploy on Railway

The public dashboard is live at [https://web-production-f02c6.up.railway.app](https://web-production-f02c6.up.railway.app) (API: [https://api-production-fa1ed.up.railway.app](https://api-production-fa1ed.up.railway.app)). Four Railway services (Postgres with pgvector, API, worker, web) deploy from this repo. See `deploy/railway.md`.

## Screenshots

Place Phase 6 screenshots here after the first real dashboard run:

- `docs/screenshots/dashboard-1440.png`
- `docs/screenshots/dashboard-1024.png`
- `docs/screenshots/dashboard-390.png`

## What you get

- One scrolling dashboard: summary, KPIs, stars, pain points, journey, Kano, themes, IPA, trends, competitor pull, PM actions, and a collapsed More detail section
- Four frameworks: customer journey, Kano, importance–performance, feedback type / churn / competitor mentions
- Plain-language glossary behind an ⓘ on every metric
- Arabic reviews always shown with an English line underneath
- Encrypted-at-rest provider keys; no telemetry

## Settings (defaults)

| Group | Key | Default |
|---|---|---|
| Costs | `costs.max_run_cost_usd` | 25 |
| Costs | `costs.require_confirmation_above_usd` | 5 |
| Scraping | `scraping.delay_seconds` | 1.5 |
| Scraping | `scraping.country_code` | ae |
| Scraping | `scraping.languages` | [en, ar] |
| Extraction | `extraction.batch_size` | 15 |
| Extraction | `extraction.temperature` | 0 |
| Extraction | `extraction.prompt_version` | v3 |
| Aggregation | `aggregation.min_n` | 50 |
| Aggregation | `aggregation.duplicate_similarity_threshold` | 0.92 |
| Aggregation | `aggregation.incentivized_exclusion_threshold` | 0.6 |
| Display | `display.default_view` | manager |

Full labels and descriptions live in Settings and in `config/settings_defaults.yaml`.

Default model roles (editable): extract A = `gpt-5.6-terra`, extract B = `deepseek-v4-pro`, tiebreak/summarise = `gpt-5.6-sol`, translate = `deepseek-v4-flash`, embed = `text-embedding-3-small`. Prices were verified 2026-09-05 against the OpenAI and DeepSeek docs.

## Cost and time (two-company analysis)

Measured on a Keeta vs Talabat run with the default models. Scraping is free; almost all of the spend is the two extract models. After junk reviews are removed, usable rows are typically about 70% of the sample drawn.

| What you run | Reviews analysed | Expected cost | Expected time |
|---|---|---|---|
| 100 reviews each | ~200 drawn, ~138 used | **$1.21** (actual) | ~11 min first time; **3–5 min** if scrape is already in the database |
| 500 each / 1,000 total | ~1,000 drawn | about **$6** | **8–15 min** if scrape is already in the database |
| 1,000 each / 2,000 total | ~2,000 drawn | about **$12** | **15–25 min** if scrape is already in the database |

The on-screen job “estimate” can undercount if older extracts exist. Trust the actual spend on a finished job.

## Metric glossary

See `config/metrics.yaml`. Every dashboard metric uses those definitions verbatim.

## Frameworks

1. **Journey** — where in the order the complaint happens
2. **Kano** — must-be / performance / delighter
3. **Importance–performance** — mention share vs net sentiment
4. **Feedback type** — bug, feature request, complaint, praise, plus churn and competitor mentions

## Add a provider

Settings → Providers. Ships with OpenAI and DeepSeek (no keys). Add any OpenAI-compatible endpoint (name, base URL, key). Test connection makes a 1-token call. After save, only `••••last4` is shown.

## Add a company

Settings → Companies → Add company. Use Look up IDs to search both stores for the configured country.

## CLI (optional)

The CLI creates the same jobs as the UI.

```bash
rap scrape --company <slug> --store all
rap scrape --all
rap extract --role a --company <slug> --mode sync --limit 60 --dry-run
rap stats raw
rap stats quality
rap flags compute --company <slug>
rap summarize --a <slug-a> --b <slug-b> --since-launch --dry-run
```

`rap worker` runs the queue. If no worker is alive, the CLI runs the job inline.

## License

The source is public. You may use, study, modify, and share it for **non-commercial** purposes under [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0).

Allowed: personal, research, hobby, education, and nonprofit use.  
Not allowed: using the software for any commercial purpose, including selling it, offering it as a paid service, or using it in a for-profit business, without a separate commercial licence.

This is a source-available licence, not an OSI “open source” licence, because those require commercial use. See `LICENSE`.
