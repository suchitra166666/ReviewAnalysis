from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from rap.db.models import ApiCredential, Company, ReviewRaw
from rap.db.session import session_scope
from rap.scrape.lookup import lookup_company_ids
from rap.seed import seed_providers, seed_settings
from rap.settings import (
    get_setting,
    invalidate_cache,
    list_settings,
    set_settings,
)

router = APIRouter()


class SettingUpdate(BaseModel):
    values: dict[str, Any]


class ProviderUpsert(BaseModel):
    display_name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    is_openai_compatible: bool | None = None
    supports_batch: bool | None = None
    supports_structured_outputs: bool | None = None
    disable_thinking: bool | None = None


class CompanyIn(BaseModel):
    slug: str
    display_name: str
    appstore_id: str | None = None
    play_package: str | None = None
    launch_date_ae: dt.date | None = None
    is_super_app: bool = False
    aliases: list[str] = Field(default_factory=list)
    notes: str | None = None


class CompanyDelete(BaseModel):
    confirm_slug: str | None = None


def _provider_public(row: ApiCredential, visitor_keys: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    own = (visitor_keys or {}).get(row.provider_slug) or {}
    return {
        "slug": row.provider_slug,
        "display_name": row.display_name,
        "base_url": row.base_url,
        "has_key": bool(own.get("has_key")),
        "key_last4": own.get("key_last4"),
        "is_openai_compatible": row.is_openai_compatible,
        "supports_batch": row.supports_batch,
        "supports_structured_outputs": row.supports_structured_outputs,
        "disable_thinking": row.disable_thinking,
        "last_verified_at": own.get("last_verified_at"),
        "last_verify_status": own.get("last_verify_status"),
    }


def _visitor_from_header(x_visitor_id: str | None) -> str | None:
    from rap.visitors import normalize_visitor_id

    return normalize_visitor_id(x_visitor_id)


def _company_public(row: Company) -> dict[str, Any]:
    return {
        "id": row.id,
        "slug": row.slug,
        "display_name": row.display_name,
        "appstore_id": row.appstore_id,
        "play_package": row.play_package,
        "launch_date_ae": row.launch_date_ae.isoformat() if row.launch_date_ae else None,
        "is_super_app": row.is_super_app,
        "aliases": row.aliases or [],
        "notes": row.notes,
        "hidden": row.hidden,
    }


@router.get("/settings")
def get_settings() -> list[dict[str, Any]]:
    return list_settings()


@router.put("/settings")
def put_settings(body: SettingUpdate) -> dict[str, Any]:
    changed = set_settings(body.values)
    return {"changed": changed}


@router.post("/settings/reset")
def reset_settings() -> dict[str, str]:
    with session_scope() as session:
        seed_settings(session, replace=True)
    invalidate_cache()
    return {"status": "reset"}


@router.get("/settings/export")
def export_settings() -> dict[str, Any]:
    return {"settings": {row["key"]: row["value"] for row in list_settings()}}


@router.post("/settings/import")
def import_settings(body: SettingUpdate) -> dict[str, Any]:
    changed = set_settings(body.values)
    return {"changed": changed}


@router.get("/providers")
def get_providers(x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id")) -> list[dict[str, Any]]:
    from rap.visitors import visitor_key_public

    visitor_id = _visitor_from_header(x_visitor_id)
    own = visitor_key_public(visitor_id) if visitor_id else {}
    with session_scope() as session:
        seed_providers(session)
        rows = session.scalars(select(ApiCredential).order_by(ApiCredential.provider_slug)).all()
        return [_provider_public(r, own) for r in rows]


@router.put("/providers/{slug}")
def put_provider(
    slug: str,
    body: ProviderUpsert,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
) -> dict[str, Any]:
    visitor_id = _visitor_from_header(x_visitor_id)
    if body.api_key:
        if not visitor_id:
            raise HTTPException(400, "Add your key from the dashboard so it stays on your browser only.")
        from rap.visitors import save_visitor_key

        save_visitor_key(visitor_id, slug, body.api_key)
        body.api_key = None
    with session_scope() as session:
        row = session.scalar(select(ApiCredential).where(ApiCredential.provider_slug == slug))
        if row is None:
            if not body.display_name or not body.base_url:
                raise HTTPException(400, "display_name and base_url are required for a new provider")
            row = ApiCredential(
                provider_slug=slug,
                display_name=body.display_name,
                base_url=body.base_url,
                is_openai_compatible=body.is_openai_compatible if body.is_openai_compatible is not None else True,
                supports_batch=body.supports_batch or False,
                supports_structured_outputs=body.supports_structured_outputs or False,
                disable_thinking=body.disable_thinking or False,
            )
            session.add(row)
        else:
            if body.display_name:
                row.display_name = body.display_name
            if body.base_url:
                row.base_url = body.base_url
            if body.is_openai_compatible is not None:
                row.is_openai_compatible = body.is_openai_compatible
            if body.supports_batch is not None:
                row.supports_batch = body.supports_batch
            if body.supports_structured_outputs is not None:
                row.supports_structured_outputs = body.supports_structured_outputs
            if body.disable_thinking is not None:
                row.disable_thinking = body.disable_thinking
        session.flush()
        from rap.visitors import visitor_key_public

        own = visitor_key_public(visitor_id) if visitor_id else {}
        return _provider_public(row, own)


@router.delete("/providers/{slug}")
def delete_provider(slug: str) -> dict[str, str]:
    if slug in {"openai", "deepseek"}:
        raise HTTPException(400, "Built-in providers cannot be deleted; clear the key instead.")
    with session_scope() as session:
        row = session.scalar(select(ApiCredential).where(ApiCredential.provider_slug == slug))
        if row is None:
            raise HTTPException(404, "Provider not found")
        session.delete(row)
    return {"status": "deleted"}


@router.post("/providers/{slug}/test")
def test_provider(slug: str, x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id")) -> dict[str, Any]:
    from rap.llm.client import test_connection
    from rap.llm.context import current_visitor_id
    from rap.visitors import decrypt_visitor_key

    visitor_id = _visitor_from_header(x_visitor_id)
    if visitor_id:
        if not decrypt_visitor_key(visitor_id, slug):
            raise HTTPException(400, "Add your OpenAI or DeepSeek key to get started.")
        token = current_visitor_id.set(visitor_id)
        try:
            return test_connection(slug)
        finally:
            current_visitor_id.reset(token)
    with session_scope() as session:
        row = session.scalar(select(ApiCredential).where(ApiCredential.provider_slug == slug))
        if row is None or row.api_key_encrypted is None:
            raise HTTPException(400, "Provider has no key to test")
    return test_connection(slug)


@router.get("/companies")
def get_companies(include_hidden: bool = False) -> list[dict[str, Any]]:
    with session_scope() as session:
        q = select(Company).order_by(Company.display_name)
        if not include_hidden:
            q = q.where(Company.hidden.is_(False))
        return [_company_public(r) for r in session.scalars(q)]


@router.post("/companies")
def post_company(body: CompanyIn) -> dict[str, Any]:
    with session_scope() as session:
        existing = session.scalar(select(Company).where(Company.slug == body.slug))
        if existing:
            raise HTTPException(400, "Slug already exists")
        row = Company(**body.model_dump())
        session.add(row)
        session.flush()
        return _company_public(row)


@router.put("/companies/{slug}")
def put_company(slug: str, body: CompanyIn) -> dict[str, Any]:
    with session_scope() as session:
        row = session.scalar(select(Company).where(Company.slug == slug))
        if row is None:
            raise HTTPException(404, "Company not found")
        for key, value in body.model_dump().items():
            setattr(row, key, value)
        session.flush()
        return _company_public(row)


@router.delete("/companies/{slug}")
def delete_company(slug: str, body: CompanyDelete | None = None) -> dict[str, Any]:
    with session_scope() as session:
        row = session.scalar(select(Company).where(Company.slug == slug))
        if row is None:
            raise HTTPException(404, "Company not found")
        n = session.scalar(select(func.count()).select_from(ReviewRaw).where(ReviewRaw.company_id == row.id)) or 0
        if n and (not body or body.confirm_slug != slug):
            raise HTTPException(
                400,
                f"This company has {n} reviews. Type the slug to confirm a soft delete.",
            )
        row.hidden = True
        return _company_public(row)


@router.post("/companies/lookup")
def lookup_companies(name: str) -> dict[str, Any]:
    return lookup_company_ids(name, get_setting("scraping.country_code", "ae"))


@router.get("/setup-status")
def setup_status(x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id")) -> dict[str, Any]:
    from rap.visitors import visitor_has_key

    visitor_id = _visitor_from_header(x_visitor_id)
    with session_scope() as session:
        n_companies = session.scalar(
            select(func.count()).select_from(Company).where(Company.hidden.is_(False))
        ) or 0
    return {
        "ready": n_companies >= 2,
        "has_own_key": bool(visitor_id and visitor_has_key(visitor_id)),
        "companies": int(n_companies),
    }
