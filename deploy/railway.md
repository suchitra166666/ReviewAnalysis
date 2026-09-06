# Railway

Four services in one project: **Postgres (pgvector image)**, **api**, **worker**, **web**.

Railway does not run `docker-compose.yml`. Each Compose service is a Railway service pointing at this repo.

## Services

| Service | Source | Start | Public |
|---|---|---|---|
| Postgres | Docker image `pgvector/pgvector:pg16` + a volume on `/var/lib/postgresql/data` | image default | no |
| api | repo root `Dockerfile` | `rap api --host 0.0.0.0` (reads `PORT`) | yes |
| worker | same image as api | `rap worker` | no |
| web | `web/Dockerfile` | `node server.js` | yes |

## Variables

Shared (or set on api + worker):

- `SETTINGS_ENCRYPTION_KEY` — Fernet key from `make init` (same value on api and worker)
- `DATABASE_URL` — `${{Postgres.DATABASE_URL}}` rewritten by the app to `postgresql+psycopg://`

Web:

- `API_INTERNAL_URL` — `http://${{api.RAILWAY_PRIVATE_DOMAIN}}:8000` (set `PORT=8000` on api so this port matches)
- `PORT` — Railway sets this; pin api to `8000`

After the first deploy, open the **web** URL, paste OpenAI/DeepSeek keys in Settings, then run the pipeline. Keys stay in the encrypted Settings store, not in Railway variables.
