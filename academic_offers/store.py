"""SQLite store. Keeps every offer ever seen, with first/last seen dates, plus one row per source per run.

An offer is "current" when the latest successful run of its source still listed it and its deadline
hasn't passed. A source that crashes records no run, so its previous offers stay up rather than vanish;
a source that runs fine and finds nothing records a run with 0, so its old offers disappear.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

from .models import Offer

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    data TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_at TEXT NOT NULL,
    source TEXT NOT NULL,
    n_offers INTEGER NOT NULL
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    _migrate_local_times(db)
    return db


# Runs recorded before timestamps were UTC, on the author's laptop (Madrid, UTC+1 in winter).
# Converted once to UTC so they sort correctly against GitHub's runs.
_LOCAL_RUNS = {"2026-11-27T11:17:09": "2026-11-27T10:17:09Z", "2026-11-27T11:23:28": "2026-11-27T10:23:28Z"}


def _migrate_local_times(db: sqlite3.Connection) -> None:
    for old, new in _LOCAL_RUNS.items():
        db.execute("UPDATE runs SET run_at = ? WHERE run_at = ?", (new, old))
        db.execute("UPDATE offers SET last_seen = ? WHERE last_seen = ?", (new, old))
    # The other naive timestamps came from GitHub Actions, which already runs in UTC.
    db.execute("UPDATE runs SET run_at = run_at || 'Z' WHERE run_at NOT LIKE '%Z'")
    db.execute("UPDATE offers SET last_seen = last_seen || 'Z' WHERE last_seen NOT LIKE '%Z'")
    db.commit()


def save(db: sqlite3.Connection, results: dict[str, list[Offer]], today: dt.date) -> str:
    """`results` maps source key → offers, for the sources that ran successfully."""
    # Always UTC: runs happen both on GitHub (UTC) and on laptops (Madrid time), and "latest run"
    # is decided by comparing these strings.
    t = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for source, offers in results.items():
        for o in offers:
            db.execute(
                """INSERT INTO offers (id, source, data, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET data = excluded.data, source = excluded.source,
                                                 last_seen = excluded.last_seen""",
                (o.id, source, json.dumps(o.to_dict(), ensure_ascii=False), today.isoformat(), t),
            )
        db.execute("INSERT INTO runs VALUES (?, ?, ?)", (t, source, len(offers)))
    db.commit()
    return t


def last_runs(db: sqlite3.Connection) -> dict[str, tuple[str, int]]:
    """source → (time of its latest successful run, items found)."""
    rows = db.execute(
        """SELECT r.source, r.run_at, r.n_offers FROM runs r
           JOIN (SELECT source, MAX(run_at) m FROM runs GROUP BY source) x
             ON r.source = x.source AND r.run_at = x.m"""
    ).fetchall()
    return {s: (t, n) for s, t, n in rows}


def previous_count(db: sqlite3.Connection, source: str, before: str) -> int | None:
    row = db.execute("SELECT n_offers FROM runs WHERE source = ? AND run_at < ? ORDER BY run_at DESC LIMIT 1",
                     (source, before)).fetchone()
    return row[0] if row else None


def current(db: sqlite3.Connection, today: dt.date) -> list[dict]:
    runs = last_runs(db)
    out = []
    for source, data, first_seen, last_seen in db.execute("SELECT source, data, first_seen, last_seen FROM offers"):
        if source not in runs or last_seen != runs[source][0]:
            continue
        d = json.loads(data)
        if d.get("deadline") and d["deadline"] < today.isoformat():
            continue
        d["first_seen"] = first_seen
        out.append(d)
    return out
