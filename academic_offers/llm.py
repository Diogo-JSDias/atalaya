"""Optional AI extraction for notices the regex parser can't read (posts listed in a table or a
separate PDF annex).

Runs only when ANTHROPIC_API_KEY is set. Every result is cached in data/llm_cache.json (committed
with the database), so each notice is paid for once. ATALAYA_LLM_MAX_CALLS caps new calls per run.
Model: ATALAYA_LLM_MODEL, default Claude Haiku 5.5 (the cheap tier agreed for bulk extraction).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

MODEL = os.environ.get("ATALAYA_LLM_MODEL", "claude-haiku-5-5")
MAX_CALLS = int(os.environ.get("ATALAYA_LLM_MAX_CALLS", "40"))
CACHE = Path(__file__).resolve().parent.parent / "data" / "llm_cache.json"
MAX_TEXT_CHARS = 120_000
MAX_PDF_BYTES = 20 * 1024 * 1024

SYSTEM = (
    "You extract structured data from Spanish official notices (BOE, university resolutions) that call "
    "academic posts. List every post being called, not the selection committees, not the people named, "
    "and not posts that are only mentioned. Copy the 'área de conocimiento' exactly as written. "
    "If the notice calls no academic posts (e.g. it is a correction or a staff exam), return an empty list."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "posts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "area": {"type": "string", "description": "Área de conocimiento, verbatim"},
                    "category": {
                        "type": "string",
                        "description": "e.g. Catedrático/a de Universidad, Profesor/a Titular de Universidad, "
                                       "Profesor/a Permanente Laboral, Profesor/a Ayudante Doctor/a",
                    },
                    "department": {"type": "string"},
                    "n_posts": {"type": "integer"},
                },
                "required": ["area", "category", "department", "n_posts"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["posts"],
    "additionalProperties": False,
}

_calls = 0
_cache: dict | None = None


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    return _cache


def _save() -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(_load(), ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def extract_posts(key: str, title: str, text: str, pdfs: list[bytes] = ()) -> list[dict] | None:
    """Return the posts called by a notice, or None if extraction is unavailable/failed."""
    cache = _load()
    if key in cache:
        return cache[key]
    global _calls
    if not enabled() or _calls >= MAX_CALLS:
        return None

    import anthropic  # imported lazily so the scraper runs without the SDK installed

    content: list[dict] = []
    for pdf in pdfs:
        if len(pdf) <= MAX_PDF_BYTES:
            content.append({"type": "document", "source": {
                "type": "base64", "media_type": "application/pdf", "data": base64.b64encode(pdf).decode()}})
    content.append({"type": "text", "text": f"Notice title: {title}\n\nNotice text:\n{text[:MAX_TEXT_CHARS]}"})

    _calls += 1
    try:
        resp = anthropic.Anthropic().messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
    except anthropic.RateLimitError:
        log.warning("LLM rate-limited; skipping %s", key)
        return None
    except anthropic.APIStatusError as e:
        log.warning("LLM error %s for %s: %s", e.status_code, key, e.message)
        return None
    except anthropic.APIConnectionError:
        log.warning("LLM connection error for %s", key)
        return None

    if resp.stop_reason != "end_turn":
        log.warning("LLM stopped with %s for %s (request %s)", resp.stop_reason, key, resp._request_id)
        return None
    text_out = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        posts = json.loads(text_out)["posts"]
    except (ValueError, KeyError):
        log.warning("LLM returned unparseable output for %s", key)
        return None

    cache[key] = posts
    _save()
    log.info("LLM extracted %d posts from %s (%d in / %d out tokens)",
             len(posts), key, resp.usage.input_tokens, resp.usage.output_tokens)
    return posts
