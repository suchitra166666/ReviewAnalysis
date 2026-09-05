from __future__ import annotations

import json
import time
from typing import Any

from rap.llm.concurrency import run_on_provider

from openai import OpenAI
from sqlalchemy import select

from rap.db.models import ApiCredential, LlmCall, LlmPurpose
from rap.db.session import session_scope
from rap.llm.context import current_job_id
from rap.settings import (
    decrypt_key,
    get_setting,
    model_price,
    role_config,
)

SYSTEM_PROMPTS: dict[str, str] = {}


def load_prompt(name: str) -> str:
    if name in SYSTEM_PROMPTS:
        return SYSTEM_PROMPTS[name]
    from rap.paths import PROMPTS_DIR

    text = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    SYSTEM_PROMPTS[name] = text
    return text


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int, cached: int = 0, batch: bool = False) -> float:
    price = model_price(model_id)
    mult = float(price.get("batch_multiplier") or 1.0) if batch else 1.0
    inp = float(price.get("input") or 0) * (input_tokens / 1_000_000)
    out = float(price.get("output") or 0) * (output_tokens / 1_000_000)
    cached_c = float(price.get("cached_input") or 0) * (cached / 1_000_000)
    return (inp + out + cached_c) * mult


def _provider_row(slug: str) -> ApiCredential:
    with session_scope() as session:
        row = session.scalar(select(ApiCredential).where(ApiCredential.provider_slug == slug))
        if row is None:
            raise RuntimeError(f"Unknown provider: {slug}")
        session.expunge(row)
        return row


def _client_for(slug: str) -> tuple[OpenAI, ApiCredential, str]:
    row = _provider_row(slug)
    if not row.api_key_encrypted:
        raise RuntimeError(
            f"Provider {slug} has no API key. Add it in Settings. There is no environment-variable fallback."
        )
    key = decrypt_key(row.api_key_encrypted)
    client = OpenAI(api_key=key, base_url=row.base_url)
    return client, row, key


def call_llm(
    *,
    purpose: LlmPurpose,
    role: str,
    messages: list[dict[str, str]],
    schema: dict[str, Any] | None = None,
    json_object: bool = False,
    n_items: int = 1,
    dry_run: bool = False,
) -> dict[str, Any]:
    cfg = role_config(role)
    provider = cfg["provider"]
    model = cfg["model"]
    temperature = float(get_setting("extraction.temperature", 0) or 0)
    if dry_run:
        return {
            "content": "",
            "model_id": model,
            "provider": provider,
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
            "est_cost_usd": 0.0,
            "latency_ms": 0,
            "request_id": None,
            "dry_run": True,
        }

    client, cred, _key = _client_for(provider)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    # gpt-5.x and some other chat models reject temperature=0; omit the default.
    if temperature not in (0, 0.0):
        kwargs["temperature"] = temperature
    if cred.supports_structured_outputs and schema is not None:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "rap_payload",
                "strict": True,
                "schema": schema,
            },
        }
    elif json_object or not cred.supports_structured_outputs:
        kwargs["response_format"] = {"type": "json_object"}
    extra_body: dict[str, Any] = {}
    if cred.disable_thinking:
        extra_body["thinking"] = {"type": "disabled"}
    if extra_body:
        kwargs["extra_body"] = extra_body

    started = time.perf_counter()
    status = "ok"
    error = None
    content = ""
    request_id = None
    usage = {"input": 0, "output": 0, "cached": 0}
    try:
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:
            text = str(exc).lower()
            if "temperature" in kwargs and "temperature" in text and "unsupported" in text:
                kwargs.pop("temperature", None)
                response = client.chat.completions.create(**kwargs)
            else:
                raise
        request_id = getattr(response, "id", None)
        content = response.choices[0].message.content or ""
        if response.usage:
            usage["input"] = int(getattr(response.usage, "prompt_tokens", 0) or 0)
            usage["output"] = int(getattr(response.usage, "completion_tokens", 0) or 0)
            details = getattr(response.usage, "prompt_tokens_details", None)
            if details is not None:
                usage["cached"] = int(getattr(details, "cached_tokens", 0) or 0)
    except Exception as exc:
        status = "error"
        error = str(exc)
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        cost = estimate_cost(model, usage["input"], usage["output"], usage["cached"])
        with session_scope() as session:
            session.add(
                LlmCall(
                    purpose=purpose,
                    model_id=model,
                    provider=provider,
                    request_id=request_id,
                    n_items=n_items,
                    input_tokens=usage["input"],
                    output_tokens=usage["output"],
                    cached_input_tokens=usage["cached"],
                    est_cost_usd=cost,
                    latency_ms=latency_ms,
                    status=status,
                    error=error,
                    job_id=current_job_id.get(),
                )
            )

    return {
        "content": content,
        "model_id": model,
        "provider": provider,
        "input_tokens": usage["input"],
        "output_tokens": usage["output"],
        "cached_input_tokens": usage["cached"],
        "est_cost_usd": estimate_cost(model, usage["input"], usage["output"], usage["cached"]),
        "latency_ms": latency_ms,
        "request_id": request_id,
    }


async def call_llm_async(**kwargs: Any) -> dict[str, Any]:
    cfg = role_config(kwargs["role"])
    return await run_on_provider(cfg["provider"], lambda: call_llm(**kwargs))


async def embed_texts_async(texts: list[str], dry_run: bool = False) -> list[list[float]]:
    cfg = role_config("embed")
    return await run_on_provider(cfg["provider"], lambda: embed_texts(texts, dry_run=dry_run))


def parse_json_content(content: str) -> Any:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def test_connection(slug: str) -> dict[str, Any]:
    import datetime as dt

    client, cred, _ = _client_for(slug)
    model = _probe_model(slug)
    status = "failed"
    error: str | None = None
    note: str | None = None
    extra: dict[str, Any] = {}
    if cred.disable_thinking:
        extra["extra_body"] = {"thinking": {"type": "disabled"}}
    probe_kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": "ok"}],
        **extra,
    }
    for limit in ({"max_tokens": 16}, {"max_completion_tokens": 16}):
        try:
            client.chat.completions.create(**probe_kwargs, **limit)
            status = "ok"
            error = None
            break
        except Exception as exc:
            error = str(exc)
    if status != "ok":
        try:
            client.models.list()
            status = "ok"
            note = f"Key is valid. Configured model {model} was refused: {error}"
            error = None
        except Exception as listing:
            status = "failed"
            error = error or str(listing)
    with session_scope() as session:
        row = session.scalar(select(ApiCredential).where(ApiCredential.provider_slug == slug))
        if row:
            row.last_verified_at = dt.datetime.now(dt.timezone.utc)
            row.last_verify_status = status
    return {"status": status, "error": error, "note": note, "model": model}


def _probe_model(slug: str) -> str:
    roles = get_setting("models.roles") or {}
    for name in ("extract_a", "extract_b", "tiebreak", "summarize", "translate"):
        role = roles.get(name) or {}
        if isinstance(role, dict) and role.get("provider") == slug and role.get("model"):
            return str(role["model"])
    for name, role in roles.items():
        if name == "embed" or not isinstance(role, dict):
            continue
        if role.get("provider") == slug and role.get("model"):
            return str(role["model"])
    return "gpt-4o-mini" if slug == "openai" else "deepseek-chat"


def embed_texts(texts: list[str], dry_run: bool = False) -> list[list[float]]:
    cfg = role_config("embed")
    if dry_run:
        return [[0.0] * 8 for _ in texts]
    client, _cred, _ = _client_for(cfg["provider"])
    started = time.perf_counter()
    status = "ok"
    error = None
    vectors: list[list[float]] = []
    usage = {"input": 0, "output": 0, "cached": 0}
    try:
        response = client.embeddings.create(model=cfg["model"], input=texts)
        vectors = [list(item.embedding) for item in response.data]
        if response.usage:
            usage["input"] = int(getattr(response.usage, "prompt_tokens", 0) or 0)
    except Exception as exc:
        status = "error"
        error = str(exc)
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        with session_scope() as session:
            session.add(
                LlmCall(
                    purpose=LlmPurpose.embed,
                    model_id=cfg["model"],
                    provider=cfg["provider"],
                    request_id=None,
                    n_items=len(texts),
                    input_tokens=usage["input"],
                    output_tokens=0,
                    cached_input_tokens=0,
                    est_cost_usd=estimate_cost(cfg["model"], usage["input"], 0),
                    latency_ms=latency_ms,
                    status=status,
                    error=error,
                    job_id=current_job_id.get(),
                )
            )
    return vectors
