from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from time import mktime, struct_time

import feedparser
from bs4 import BeautifulSoup

from fetch import PoliteFetcher
from sources import FeedSource

def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")[:80] or "item"

def _to_datetime(parsed: struct_time | None) -> datetime | None:
    if not parsed:
        return None
    try:
        return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
    except (OverflowError, ValueError, TypeError):
        return None

def _clean_tags(raw_tags) -> list[str]:
    out: list[str] = []
    for t in raw_tags or []:
        term = getattr(t, "term", None) or (t.get("term") if isinstance(t, dict) else None)
        if term:
            out.append(term.strip().lower())
    return out

def _guess_difficulty(title: str, tags: list[str]) -> str:
    haystack = " ".join([title.lower(), *tags])
    if any(w in haystack for w in ("insane", "hard", "advanced", "expert")):
        return "advanced"
    if any(w in haystack for w in ("easy", "beginner", "intro", "basics")):
        return "beginner"
    return "intermediate"

def _ingest_feed(text: str, src: FeedSource, now: datetime) -> list[dict]:
    parsed = feedparser.parse(text)
    entries: list[dict] = []
    for item in parsed.entries:
        link = getattr(item, "link", None)
        title = (getattr(item, "title", "") or "").strip()
        if not link or not title:
            continue
        tags = list(dict.fromkeys(_clean_tags(getattr(item, "tags", None)) + list(src.default_tags)))
        published = _to_datetime(getattr(item, "published_parsed", None)
                                 or getattr(item, "updated_parsed", None))
        summary = ""
        raw_summary = getattr(item, "summary", "") or ""
        if raw_summary:
            summary = BeautifulSoup(raw_summary, "lxml").get_text(" ", strip=True)[:280]

        entries.append(_make_resource(src, link, title, tags, summary, published, now))
    return entries

def _ingest_sitemap(text: str, src: FeedSource, now: datetime) -> list[dict]:
    soup = BeautifulSoup(text, "xml")
    entries: list[dict] = []
    for url_node in soup.find_all("url"):
        loc = url_node.find("loc")
        if loc is None or not loc.text.strip():
            continue
        link = loc.text.strip()
        slug = link.rstrip("/").rsplit("/", 1)[-1]
        title = slug.replace("-", " ").replace("_", " ").strip().title() or link
        lastmod = url_node.find("lastmod")
        published = None
        if lastmod is not None and lastmod.text.strip():
            try:
                published = datetime.fromisoformat(
                    lastmod.text.strip().replace("Z", "+00:00")
                ).astimezone(timezone.utc)
            except ValueError:
                published = None
        tags = list(src.default_tags)
        entries.append(_make_resource(src, link, title, tags, "", published, now))
    return entries

def _make_resource(src: FeedSource, url: str, title: str, tags: list[str],
                   summary: str, published: datetime | None, now: datetime) -> dict:
    return {
        "id": f"res:{src.id}.{_slug(title)}",
        "kind": "resource",
        "title": title,
        "summary": summary,
        "url": url,
        "source_id": src.id,
        "tags": tags,
        "categories": list(src.default_categories),
        "os": ["cross-platform"],
        "difficulty": _guess_difficulty(title, tags),
        "keywords": [src.name, src.author or ""],
        "indexed_at": now.isoformat(),
        "_published": published,
    }

def _ingest_ippsec_json(text: str, src: FeedSource, now: datetime) -> list[dict]:
    rows = json.loads(text)
    granularity = (src.options or {}).get("granularity", "video")
    now_iso = now.isoformat()

    def yt_url(video_id: str, seconds: int) -> str:
        base = f"https://www.youtube.com/watch?v={video_id}"
        return f"{base}&t={seconds}" if seconds else base

    def row_seconds(row: dict) -> int:
        ts = row.get("timestamp") or {}
        return int(ts.get("minutes", 0)) * 60 + int(ts.get("seconds", 0))

    def row_tags(row: dict) -> list[str]:
        raw = (row.get("tag") or "").strip().lower()
        tags = [t for t in raw.replace(",", " ").split() if t]
        return list(dict.fromkeys(tags + list(src.default_tags)))

    if granularity == "chapter":
        entries: list[dict] = []
        for row in rows:
            machine = (row.get("machine") or "").strip()
            line = (row.get("line") or "").strip()
            if not machine or not line:
                continue
            if "videoId" in row:
                url = yt_url(row["videoId"], row_seconds(row))
            elif "academy" in row:
                url = f"https://academy.hackthebox.eu/module/details/{row['academy']}"
            else:
                continue
            title = f"{machine} - {line}" if line else machine
            entries.append(_make_resource(src, url, title[:120], row_tags(row),
                                          line[:280], None, now))
        return _dedup(entries)

    groups: dict[str, dict] = {}
    for row in rows:
        machine = (row.get("machine") or "").strip()
        if not machine:
            continue
        if "videoId" in row:
            key = f"v:{row['videoId']}"
            url = yt_url(row["videoId"], 0)
        elif "academy" in row:
            key = f"a:{row['academy']}"
            url = f"https://academy.hackthebox.eu/module/details/{row['academy']}"
        else:
            continue
        g = groups.setdefault(key, {"machine": machine, "url": url,
                                    "tags": set(), "chapters": []})
        g["tags"].update(row_tags(row))
        line = (row.get("line") or "").strip()
        if line:
            g["chapters"].append(line)

    entries = []
    for g in groups.values():
        keywords = list(dict.fromkeys(
            [src.name, src.author or ""] + g["chapters"][:25]
        ))
        summary = ""
        if g["chapters"]:
            summary = "Covers: " + "; ".join(g["chapters"][:6])
        entries.append({
            "id": f"res:{src.id}.{_slug(g['machine'])}",
            "kind": "resource",
            "title": g["machine"],
            "summary": summary[:280],
            "url": g["url"],
            "source_id": src.id,
            "tags": sorted(g["tags"]),
            "categories": list(src.default_categories),
            "os": ["cross-platform"],
            "difficulty": _guess_difficulty(g["machine"], sorted(g["tags"])),
            "keywords": [k for k in keywords if k],
            "indexed_at": now_iso,
            "_published": None,
        })
    return _dedup(entries)

def _dedup(entries: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for e in entries:
        seen.setdefault(e["id"], e)
    return list(seen.values())

def ingest_source(fetcher: PoliteFetcher, src: FeedSource,
                  now: datetime | None = None) -> list[dict]:

    now = now or datetime.now(timezone.utc)
    try:
        text = fetcher.fetch(src.feed_url, delay=src.request_delay)
    except Exception as exc:
        print(f"  ! {src.id}: fetch failed ({exc}); skipping this source")
        return []

    try:
        if src.feed_kind == "sitemap":
            entries = _ingest_sitemap(text, src, now)
        elif src.feed_kind == "ippsec-json":
            entries = _ingest_ippsec_json(text, src, now)
        else:
            entries = _ingest_feed(text, src, now)
    except Exception as exc:
        print(f"  ! {src.id}: parse failed ({exc}); skipping this source")
        return []

    result = _dedup(entries)

    if src.coverage_url:
        result = _merge_coverage(fetcher, src, result, now)

    print(f"  + {src.id}: {len(result)} entries")
    return result

def _merge_coverage(fetcher: PoliteFetcher, src: FeedSource,
                    feed_entries: list[dict], now: datetime) -> list[dict]:
    try:
        text = fetcher.fetch(src.coverage_url, delay=src.request_delay)
    except Exception as exc:
        print(f"    ~ {src.id}: coverage sitemap unavailable ({exc}); feed only")
        return feed_entries

    try:
        soup = BeautifulSoup(text, "xml")
    except Exception as exc:
        print(f"    ~ {src.id}: coverage parse failed ({exc}); feed only")
        return feed_entries

    have_urls = {e["url"] for e in feed_entries}
    pattern = re.compile(src.coverage_url_pattern) if src.coverage_url_pattern else None
    added: list[dict] = []

    for loc in soup.find_all("loc"):
        url = (loc.text or "").strip()
        if not url or url in have_urls:
            continue
        if pattern and not pattern.search(url):
            continue
        slug = url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".html")
        title = slug.replace("-", " ").replace("_", " ").strip().title() or url
        lastmod_node = loc.find_next_sibling("lastmod")
        published = None
        if lastmod_node is not None and lastmod_node.text.strip():
            try:
                published = datetime.fromisoformat(
                    lastmod_node.text.strip().replace("Z", "+00:00")
                ).astimezone(timezone.utc)
            except ValueError:
                published = None
        added.append(_make_resource(src, url, title, list(src.default_tags),
                                    "", published, now))
        have_urls.add(url)

    if added:
        print(f"    + {src.id}: coverage added {len(added)} back-catalogue entries")
    return _dedup(feed_entries + added)
