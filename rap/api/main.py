from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rap.api.routes import analysis, health, history, jobs, presence, settings
from rap.env import settings_encryption_key
from rap.logging_util import configure_logging
from rap.settings import bootstrap, stored_key_fragments


def create_app() -> FastAPI:
    from rap.db.migrate import upgrade_head

    try:
        settings_encryption_key()
    except RuntimeError as exc:
        raise RuntimeError(
            "SETTINGS_ENCRYPTION_KEY is missing. Run `make init` before starting the API."
        ) from exc
    upgrade_head()
    formatter = configure_logging()
    bootstrap()
    formatter.set_secrets(stored_key_fragments())
    app = FastAPI(title="Review Analysis Platform", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_origin_regex=r"https://.*\.(up\.railway\.app|railway\.app)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(analysis.router)
    app.include_router(settings.router)
    app.include_router(jobs.router)
    app.include_router(history.router)
    app.include_router(presence.router)
    return app


app = create_app()
