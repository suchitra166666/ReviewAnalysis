# Contributing

## Local setup

1. Install Python 3.11+, [uv](https://github.com/astral-sh/uv), Docker, and Node 20.
2. `make init`
3. `uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"`
4. `docker compose up postgres -d`
5. `make migrate`
6. `rap api` and `rap worker` in two terminals, or `docker compose up`.
7. `cd web && npm install && npm run dev`

## Rules

- Do not add environment variables beyond `DATABASE_URL` and `SETTINGS_ENCRYPTION_KEY`.
- Do not hardcode company slugs, model IDs, or API keys in application code.
- Every LLM call goes through `rap/llm/client.py`.
- Every metric on the dashboard uses `<MetricLabel>`.
- Arabic review text always ships with an `EN:` line.
- Tests: `pytest -q` and `cd web && npm test`.

## Pull requests

Keep changes small. Update `docs/build-log.md` when you finish a phase-sized piece of work.
