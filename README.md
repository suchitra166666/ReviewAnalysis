# Review Analysis Platform (RAP)

Compares two food-delivery companies from public App Store and Google Play reviews. Reviews are labelled with two independent LLMs against a fixed theme taxonomy, then shown on a two-company dashboard.

**Live:** [https://web-production-f02c6.up.railway.app](https://web-production-f02c6.up.railway.app)

On the live site, add your own OpenAI or DeepSeek key to run analysis. Host keys are not used.

## Run locally

```bash
git clone https://github.com/suchitra166666/ReviewAnalysis.git
cd ReviewAnalysis
make init
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). Add a provider key in Settings, then run a scrape and analysis from Jobs.

`make init` writes `.env` with `DATABASE_URL` and `SETTINGS_ENCRYPTION_KEY`. Everything else is edited in Settings.

## What you get

- One scrolling dashboard: summary, key numbers, stars, pain points, journey, Kano, themes, IPA, trends, competitor pull, and PM actions
- Plain-language glossary behind an ⓘ on every metric
- Arabic reviews shown with an English line underneath
- Encrypted provider keys; no telemetry

## Cost and time

Measured on a Keeta vs Talabat run with the default models. Scraping is free; almost all of the spend is the two extract models.

| What you run | Reviews analysed | Expected cost | Expected time |
|---|---|---|---|
| 100 reviews each | ~200 drawn, ~138 used | **$1.21** (actual) | ~11 min first time; **3–5 min** if scrape is already in the database |
| 500 each / 1,000 total | ~1,000 drawn | about **$6** | **8–15 min** if scrape is already in the database |
| 1,000 each / 2,000 total | ~2,000 drawn | about **$12** | **15–25 min** if scrape is already in the database |

## License

The source is public. You may use, study, modify, and share it for **non-commercial** purposes under [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0).

Allowed: personal, research, hobby, education, and nonprofit use.  
Not allowed: using the software for any commercial purpose, including selling it, offering it as a paid service, or using it in a for-profit business, without a separate commercial licence.

This is a source-available licence, not an OSI “open source” licence, because those require commercial use. See `LICENSE`.
