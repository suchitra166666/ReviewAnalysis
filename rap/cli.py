from __future__ import annotations

import json
import time
from typing import Optional

import typer
from sqlalchemy import select

from rap.db.models import Company, Job, JobKind, JobStatus
from rap.db.session import session_scope
from rap.jobs.queue import ConfirmationRequired, CostCapExceeded, create_job, get_job
from rap.seed import seed_companies, seed_if_empty
from rap.settings import bootstrap

app = typer.Typer(help="Review Analysis Platform")
companies_app = typer.Typer(help="Company seed commands")
stats_app = typer.Typer(help="Stats commands")
flags_app = typer.Typer(help="Review-flag commands")
app.add_typer(companies_app, name="companies")
app.add_typer(stats_app, name="stats")
app.add_typer(flags_app, name="flags")


def _boot() -> None:
    bootstrap()


def _resolve_slugs(company: Optional[str], all_companies: bool) -> list[str]:
    _boot()
    with session_scope() as session:
        if all_companies:
            return list(
                session.scalars(select(Company.slug).where(Company.hidden.is_(False)).order_by(Company.slug))
            )
        if not company:
            raise typer.BadParameter("Pass --company <slug> or --all")
        row = session.scalar(select(Company).where(Company.slug == company))
        if row is None:
            raise typer.BadParameter(f"Unknown company: {company}")
        return [row.slug]


def _company_ids(slugs: list[str]) -> list[int]:
    with session_scope() as session:
        rows = session.scalars(select(Company).where(Company.slug.in_(slugs))).all()
        return [r.id for r in rows]


def _submit_and_run(
    kind: JobKind,
    params: dict,
    dry_run: bool,
    confirm: bool,
    queue_only: bool,
) -> None:
    _boot()
    try:
        job = create_job(kind, params, confirm=confirm, dry_run=dry_run)
    except CostCapExceeded as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2)
    except ConfirmationRequired as exc:
        typer.echo(str(exc))
        typer.echo("Re-run with --confirm to proceed (Checkpoint C).")
        raise typer.Exit(code=3)
    if dry_run:
        typer.echo(f"dry-run {kind.value} estimate ${job.est_cost_usd:.4f}")
        return
    typer.echo(f"job {job.id} queued ({kind.value}) estimate ${job.est_cost_usd:.4f}")
    if queue_only:
        return
    _run_or_tail(job.id)


def _worker_alive() -> bool:
    from rap.jobs.worker import last_heartbeat
    import datetime as dt

    seen = last_heartbeat()
    if seen is None:
        return False
    now = dt.datetime.now(dt.timezone.utc)
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=dt.timezone.utc)
    return (now - seen).total_seconds() < 15


def _run_or_tail(job_id: int) -> None:
    if not _worker_alive():
        from rap.jobs.handlers import handle_job
        from rap.db.session import session_scope as scope

        with scope() as session:
            job = session.get(Job, job_id)
            if job and job.status == JobStatus.queued:
                job.status = JobStatus.running
                import datetime as dt

                job.started_at = dt.datetime.now(dt.timezone.utc)
        handle_job(job_id)
        with scope() as session:
            job = session.get(Job, job_id)
            if job and job.status == JobStatus.running:
                import datetime as dt

                job.status = JobStatus.ok
                job.finished_at = dt.datetime.now(dt.timezone.utc)
        job = get_job(job_id)
        if job:
            typer.echo(job.log)
            typer.echo(f"status={job.status.value}")
        return
    last_len = 0
    while True:
        job = get_job(job_id)
        if job is None:
            raise typer.Exit(code=1)
        extra = (job.log or "")[last_len:]
        if extra:
            typer.echo(extra, nl=False)
            last_len = len(job.log or "")
        if job.status in {JobStatus.ok, JobStatus.failed, JobStatus.cancelled}:
            typer.echo(f"status={job.status.value}")
            if job.status != JobStatus.ok:
                raise typer.Exit(code=1)
            return
        time.sleep(1)


@app.command()
def scrape(
    company: Optional[str] = typer.Option(None, help="Company slug"),
    all_companies: bool = typer.Option(False, "--all", help="Scrape every visible company"),
    store: str = typer.Option("all", help="appstore | play | all"),
    full: bool = typer.Option(False, "--full", help="Do not stop on a page of known IDs"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm: bool = typer.Option(False, "--confirm"),
    queue_only: bool = typer.Option(False, "--queue-only"),
) -> None:
    slugs = _resolve_slugs(company, all_companies)
    stores = ["appstore", "play"] if store == "all" else [store]
    _submit_and_run(
        JobKind.scrape,
        {"slugs": slugs, "stores": stores, "full": full},
        dry_run,
        confirm,
        queue_only,
    )


@app.command()
def extract(
    role: str = typer.Option(..., help="a or b"),
    company: Optional[str] = typer.Option(None),
    all_companies: bool = typer.Option(False, "--all"),
    mode: str = typer.Option("sync", help="sync | batch | collect"),
    limit: Optional[int] = typer.Option(None),
    sample_per_star: Optional[int] = typer.Option(None),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm: bool = typer.Option(False, "--confirm"),
    queue_only: bool = typer.Option(False, "--queue-only"),
) -> None:
    slugs = _resolve_slugs(company, all_companies)
    kind = JobKind.extract_a if role == "a" else JobKind.extract_b
    _submit_and_run(
        kind,
        {
            "slugs": slugs,
            "company_ids": _company_ids(slugs),
            "mode": mode,
            "limit": limit,
            "sample_per_star": sample_per_star,
            "role": role,
        },
        dry_run,
        confirm,
        queue_only,
    )


@app.command()
def reconcile(
    company: Optional[str] = typer.Option(None),
    all_companies: bool = typer.Option(False, "--all"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm: bool = typer.Option(False, "--confirm"),
    queue_only: bool = typer.Option(False, "--queue-only"),
) -> None:
    slugs = _resolve_slugs(company, all_companies)
    _submit_and_run(
        JobKind.reconcile,
        {"slugs": slugs, "company_ids": _company_ids(slugs)},
        dry_run,
        confirm,
        queue_only,
    )


@app.command()
def translate(
    company: Optional[str] = typer.Option(None),
    all_companies: bool = typer.Option(False, "--all"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm: bool = typer.Option(False, "--confirm"),
    queue_only: bool = typer.Option(False, "--queue-only"),
) -> None:
    slugs = _resolve_slugs(company, all_companies)
    _submit_and_run(
        JobKind.translate,
        {"slugs": slugs, "company_ids": _company_ids(slugs)},
        dry_run,
        confirm,
        queue_only,
    )


@flags_app.command("compute")
def flags_compute(
    company: Optional[str] = typer.Option(None),
    all_companies: bool = typer.Option(False, "--all"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm: bool = typer.Option(False, "--confirm"),
    queue_only: bool = typer.Option(False, "--queue-only"),
) -> None:
    slugs = _resolve_slugs(company, all_companies)
    _submit_and_run(
        JobKind.flags,
        {"slugs": slugs, "company_ids": _company_ids(slugs)},
        dry_run,
        confirm,
        queue_only,
    )


@app.command()
def summarize(
    a: str = typer.Option(..., help="Company A slug"),
    b: str = typer.Option(..., help="Company B slug"),
    since_launch: bool = typer.Option(False, "--since-launch"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    confirm: bool = typer.Option(False, "--confirm"),
    queue_only: bool = typer.Option(False, "--queue-only"),
) -> None:
    slugs = _resolve_slugs(None, False) if False else [a, b]
    # validate both exist
    _resolve_slugs(a, False)
    _resolve_slugs(b, False)
    _submit_and_run(
        JobKind.summarize,
        {"a": a, "b": b, "slugs": slugs, "since_launch": since_launch},
        dry_run,
        confirm,
        queue_only,
    )


@stats_app.command("raw")
def stats_raw() -> None:
    _boot()
    from rap.stats_cli import raw_stats

    typer.echo(json.dumps(raw_stats(), indent=2, default=str))


@stats_app.command("quality")
def stats_quality() -> None:
    _boot()
    from rap.stats_cli import quality_stats

    typer.echo(json.dumps(quality_stats(), indent=2, default=str))


@stats_app.command("exclusions")
def stats_exclusions() -> None:
    _boot()
    from rap.stats_cli import exclusion_stats

    typer.echo(json.dumps(exclusion_stats(), indent=2, default=str))


@companies_app.command("sync")
def companies_sync(from_yaml: bool = typer.Option(False, "--from-yaml")) -> None:
    _boot()
    if not from_yaml:
        typer.echo("Pass --from-yaml to re-seed companies from config/companies.yaml")
        raise typer.Exit(code=1)
    with session_scope() as session:
        seed_companies(session, replace=True)
    typer.echo("Companies re-seeded from YAML.")


@app.command()
def worker() -> None:
    from rap.jobs.worker import run_forever

    run_forever()


@app.command()
def api(host: str = "0.0.0.0", port: int = 8000) -> None:
    import os

    import uvicorn

    bound = int(os.environ.get("PORT") or port)
    uvicorn.run("rap.api.main:app", host=host, port=bound, factory=False)


@app.command("print-extract")
def print_extract(company: str, limit: int = 10) -> None:
    """Print extracted rows next to raw text (Checkpoint B helper)."""
    _boot()
    from rap.db.models import ReviewExtracted, ReviewRaw

    with session_scope() as session:
        company_row = session.scalar(select(Company).where(Company.slug == company))
        if company_row is None:
            raise typer.BadParameter(company)
        rows = session.execute(
            select(ReviewRaw, ReviewExtracted)
            .join(ReviewExtracted, ReviewExtracted.review_id == ReviewRaw.id)
            .where(ReviewRaw.company_id == company_row.id, ReviewExtracted.role == "a")
            .limit(limit)
        ).all()
        for raw, ext in rows:
            typer.echo("=" * 72)
            typer.echo(f"id={raw.id} stars={raw.star_rating} {raw.review_date.date()} {raw.store.value}")
            typer.echo(f"RAW: {(raw.title or '')} — {raw.body}")
            typer.echo(
                f"labels: sentiment={ext.overall_sentiment} lang={ext.language} "
                f"food={ext.is_food_related} type={ext.feedback_type} "
                f"churn={ext.churn_intent} incentive={ext.mentions_incentive}"
            )
            for mention in ext.mentions or []:
                snippet = mention.get("snippet")
                snippet_en = mention.get("snippet_en")
                typer.echo(
                    f"  - {mention.get('theme')}/{mention.get('sub_theme')} "
                    f"{mention.get('sentiment')} :: {snippet}"
                )
                if snippet_en:
                    typer.echo(f"    EN: {snippet_en}")


@app.callback()
def main() -> None:
    """RAP CLI."""
    return


if __name__ == "__main__":
    app()
