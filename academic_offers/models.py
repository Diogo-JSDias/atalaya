from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from dataclasses import field as dc_field
from typing import Optional


@dataclass
class Offer:
    """One position or one funding call, normalised across sources."""

    source: str                      # e.g. "boe", "cnic", "eu-ft"
    kind: str                        # "position" | "call"
    title: str
    url: str
    institution: str = ""
    region: str = ""                 # Comunidad autónoma, or "Europe"
    position_type: str = ""          # e.g. "Profesor Titular", "Postdoc", "Fellowship"
    stage: str = ""                  # career stage, filled by classify.py
    area_raw: str = ""               # area exactly as the source states it
    field: str = ""                  # broad field (see classify.py)
    subfield: str = ""
    deadline: Optional[str] = None   # ISO date
    deadline_estimated: bool = False # True when computed (e.g. "15 días hábiles")
    published: Optional[str] = None  # ISO date
    n_posts: int = 1
    notes: str = ""
    extra: dict = dc_field(default_factory=dict)

    @property
    def id(self) -> str:
        key = f"{self.source}|{self.url}|{self.title}|{self.area_raw}"
        return hashlib.sha1(key.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d
