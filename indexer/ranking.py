from __future__ import annotations

from datetime import datetime, timezone
import math

_KIND_BASE = {"command": 3.0, "resource": 2.0}

_W_HAS_SUMMARY = 0.5
_W_PER_TAG = 0.15
_W_PER_CATEGORY = 0.25    
_W_PER_FLAG = 0.05        
_W_PER_EXAMPLE = 0.4       
_W_HAS_BREAKDOWN = 0.6

_FRESHNESS_MAX = 1.5
_FRESHNESS_HALFLIFE_DAYS = 365.0

def _freshness(published: datetime | None, now: datetime) -> float:
    if published is None:
        return 0.0
    age_days = max(0.0, (now - published).total_seconds() / 86400.0)

    return _FRESHNESS_MAX * math.pow(0.5, age_days / _FRESHNESS_HALFLIFE_DAYS)

def score_entry(entry: dict, *, now: datetime | None = None) -> float:

    now = now or datetime.now(timezone.utc)
    score = _KIND_BASE.get(entry.get("kind"), 1.0)

    if entry.get("summary"):
        score += _W_HAS_SUMMARY

    score += min(len(entry.get("tags", [])) * _W_PER_TAG, 0.75)
    score += min(len(entry.get("categories", [])) * _W_PER_CATEGORY, 0.75)

    cmd = entry.get("command")
    if cmd:
        score += min(len(cmd.get("flags", [])) * _W_PER_FLAG, 0.5)
        examples = cmd.get("examples", [])
        score += min(len(examples) * _W_PER_EXAMPLE, 1.2)
        if any(ex.get("breakdown") for ex in examples):
            score += _W_HAS_BREAKDOWN

    published = entry.get("_published")
    score += _freshness(published, now)

    return round(score, 3)

def apply_ranking(entries: list[dict], *, now: datetime | None = None) -> None:

    now = now or datetime.now(timezone.utc)
    for e in entries:
        e["rank_score"] = score_entry(e, now=now)