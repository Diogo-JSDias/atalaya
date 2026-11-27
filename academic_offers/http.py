"""Polite HTTP client: identifies itself, obeys robots.txt (including Crawl-delay), waits between
requests to the same host, and caches responses so a day's run never fetches a page twice."""
from __future__ import annotations

import hashlib
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger(__name__)

SITE_URL = os.environ.get("ATALAYA_SITE_URL", "https://github.com/atalaya-es/atalaya").rstrip("/")
USER_AGENT = f"AtalayaBot/0.2 (+{SITE_URL}/about.html; once a day, non-commercial)"
BOT_NAME = "AtalayaBot"
DEFAULT_DELAY = 2.0

CACHE_DIR = Path(".cache/http")
CACHE_TTL = 6 * 3600  # seconds

_last_hit: dict[str, float] = {}
_robots: dict[str, RobotFileParser | None] = {}
_client = httpx.Client(
    headers={"User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8"},
    follow_redirects=True,
    timeout=45,
)


class Disallowed(Exception):
    """robots.txt forbids this URL for our bot."""


def _robots_for(scheme: str, host: str) -> RobotFileParser | None:
    if host not in _robots:
        rp = RobotFileParser()
        try:
            r = _client.get(f"{scheme}://{host}/robots.txt", timeout=15)
            # No robots.txt (4xx) means everything is allowed; a server error means "try later".
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            _robots[host] = rp
        except httpx.HTTPError:
            _robots[host] = None
    return _robots[host]


def _check(url: str) -> float:
    """Raise if robots.txt disallows the URL; return the delay to keep between requests."""
    u = urlparse(url)
    rp = _robots_for(u.scheme, u.netloc)
    if rp is not None and not rp.can_fetch(BOT_NAME, url):
        raise Disallowed(url)
    delay = (rp.crawl_delay(BOT_NAME) if rp else None) or DEFAULT_DELAY
    return max(float(delay), DEFAULT_DELAY)


def _wait(host: str, delay: float) -> None:
    elapsed = time.time() - _last_hit.get(host, 0)
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _last_hit[host] = time.time()


def _cached(method: str, url: str, suffix: str) -> Path:
    return CACHE_DIR / (hashlib.sha1(f"{method} {url}".encode()).hexdigest() + suffix)


def _request(url: str, method: str, headers: dict | None) -> httpx.Response:
    delay = _check(url)
    _wait(urlparse(url).netloc, delay)
    resp = _client.request(method, url, headers=headers)
    resp.raise_for_status()
    return resp


def fetch(url: str, *, method: str = "GET", headers: dict | None = None, use_cache: bool = True) -> str:
    path = _cached(method, url, "")
    if use_cache and path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL:
        return path.read_text(encoding="utf-8")
    text = _request(url, method, headers).text
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def fetch_bytes(url: str, *, use_cache: bool = True) -> bytes:
    """For PDFs. Cached for a week: published annexes don't change."""
    path = _cached("GET", url, ".bin")
    if use_cache and path.exists() and time.time() - path.stat().st_mtime < 7 * 86400:
        return path.read_bytes()
    data = _request(url, "GET", None).content
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data
