"""INESC TEC open opportunities via the official Strapi JSON API."""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from urllib.parse import urlparse

from ..http import fetch
from ..models import Offer

log = logging.getLogger(__name__)

API_URL = "https://cms.inesctec.pt/api/opportunities"
OPPORTUNITY_BASE_URL = "https://inesctec.pt/en/join-us/opportunities"
OFFICIAL_HOSTS = ("inesctec.pt", "cms.inesctec.pt")

_DOC_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _clean(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _iso_date(value: object) -> str | None:
    text = _clean(value)
    if not text:
        return None
    candidate = text[:10]
    try:
        dt.date.fromisoformat(candidate)
    except ValueError:
        return None
    return candidate


def _allowed_host(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    return parsed.scheme in {"http", "https"} and any(
        host == domain or host.endswith("." + domain) for domain in OFFICIAL_HOSTS
    )


def _build_url(today: dt.date, page: int = 1) -> str:
    query = f"filters[application_end][$gte]={today.isoformat()}&populate=*"
    if page > 1:
        query += f"&pagination[page]={page}"
    return f"{API_URL}?{query}"


def parse_opportunities(payload: dict, today: dt.date) -> list[Offer]:
    """Parse active INESC TEC opportunities from a Strapi JSON payload."""
    if not isinstance(payload, dict):
        return []
    items = payload.get("data")
    if not isinstance(items, list):
        return []

    today_iso = today.isoformat()
    offers: list[Offer] = []
    seen_urls: set[str] = set()

    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        item = raw_item.get("attributes") if isinstance(raw_item.get("attributes"), dict) else raw_item

        doc_id = _clean(item.get("documentId") or raw_item.get("documentId"))
        if not doc_id or not _DOC_ID_RE.fullmatch(doc_id):
            continue

        url = f"{OPPORTUNITY_BASE_URL}/{doc_id}"
        if not _allowed_host(url) or url in seen_urls:
            continue

        deadline = _iso_date(item.get("application_end"))
        if not deadline or deadline < today_iso:
            continue

        position = item.get("position") if isinstance(item.get("position"), dict) else {}
        structure = item.get("structure") if isinstance(item.get("structure"), dict) else {}

        title = _clean(position.get("description")) or _clean(item.get("title")) or _clean(position.get("title"))
        if not title:
            continue

        published = _iso_date(item.get("application_start"))
        region = _clean(item.get("location")) or "Norte"
        area_raw = _clean(structure.get("name"))

        is_grant = position.get("is_grant")
        if is_grant is True:
            position_type = "Grant"
        elif is_grant is False:
            position_type = "Position"
        else:
            position_type = ""

        extra: dict[str, str] = {"document_id": doc_id}
        iris_id = _clean(item.get("iris_id"))
        if iris_id:
            extra["iris_id"] = iris_id
        pdf_url = _clean(item.get("pdf_url"))
        if pdf_url and _allowed_host(pdf_url):
            extra["pdf_url"] = pdf_url

        seen_urls.add(url)
        offers.append(
            Offer(
                source="inesc-tec",
                kind="position",
                title=title,
                url=url,
                institution="INESC TEC",
                region=region,
                position_type=position_type,
                area_raw=area_raw,
                deadline=deadline,
                published=published,
                extra=extra,
            )
        )

    return offers


def scrape(today: dt.date | None = None) -> list[Offer]:
    """Fetch active INESC TEC opportunities across all result pages."""
    today = today or dt.date.today()
    offers: list[Offer] = []
    seen_urls: set[str] = set()
    page = 1
    page_count = 1

    while page <= page_count:
        raw = fetch(_build_url(today, page))
        if not raw or not raw.strip():
            break
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            log.warning("Invalid JSON from INESC TEC API (page %d): %s", page, exc)
            break
        if not isinstance(payload, dict):
            break

        for offer in parse_opportunities(payload, today):
            if offer.url not in seen_urls:
                seen_urls.add(offer.url)
                offers.append(offer)

        meta = payload.get("meta")
        pagination = meta.get("pagination") if isinstance(meta, dict) else None
        if not isinstance(pagination, dict):
            break
        try:
            page_count = max(1, int(pagination.get("pageCount") or 1))
        except (TypeError, ValueError):
            break
        page += 1

    return offers
