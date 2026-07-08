#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from commands import load_command_entries
from fetch import PoliteFetcher
from ingest import ingest_source
from ranking import apply_ranking
from sources import FEED_SOURCES, all_source_records

SCHEMA_VERSION = "1.0.0"

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
DEFAULT_COMMANDS = PROJECT / "data" / "commands.json"
DEFAULT_SCHEMA = PROJECT / "schema" / "index.schema.json"
DEFAULT_OUT = PROJECT / "site" / "index.json"
SAMPLE_DIR = HERE / "sample_feeds"

_LIST_FACETS = ("categories", "tags", "os")
_SCALAR_FACETS = ("difficulty", "kind")

def build_facets(entries: list[dict]) -> dict:
    facets: dict[str, list[dict]] = {}
    facet_key = {"categories": "categories", "tags": "tags", "os": "os"}
    for field in _LIST_FACETS:
        counter: Counter = Counter()
        for e in entries:
            counter.update(e.get(field, []))
        facets[facet_key[field]] = [
            {"value": v, "count": c} for v, c in counter.most_common()
        ]
    for field in _SCALAR_FACETS:
        counter = Counter(e.get(field) for e in entries if e.get(field))
        facets[field] = [{"value": v, "count": c} for v, c in counter.most_common()]
    return facets

def strip_internal(entries: list[dict]) -> None:
    for e in entries:
        for key in [k for k in e if k.startswith("_")]:
            e.pop(key, None)

def configure_sample_sources() -> None:
    mapping = {
        "0xdf": SAMPLE_DIR / "0xdf_feed.xml",
        "ippsec": SAMPLE_DIR / "ippsec_dataset.json",
    }
    for src in FEED_SOURCES:
        local = mapping.get(src.id)
        if local and local.exists():
            # FeedSource is frozen; rebind the private field via object.__setattr__.
            object.__setattr__(src, "feed_url", str(local))

def configure_local_feeds(directory: Path) -> None:
    for src in FEED_SOURCES:
        for ext in ("xml", "json", "atom", "rss"):
            candidate = directory / f"{src.id}.{ext}"
            if candidate.exists():
                object.__setattr__(src, "feed_url", str(candidate))
                break
        sitemap = directory / f"{src.id}.sitemap.xml"
        object.__setattr__(src, "coverage_url",
                           str(sitemap) if sitemap.exists() else None)

def build_index(*, sample: bool, commands_path: Path,
                local_feeds: Path | None = None) -> dict:
    now = datetime.now(timezone.utc)
    entries: list[dict] = []

    print("Loading curated command dataset (F2)...")
    cmd_entries = load_command_entries(commands_path, now=now)
    print(f"  + commands: {len(cmd_entries)} cards")
    entries.extend(cmd_entries)

    print("Ingesting sources (F3)...")
    offline = sample or local_feeds is not None
    fetcher = PoliteFetcher(offline=offline)
    if sample:
        configure_sample_sources()
    if local_feeds is not None:
        configure_local_feeds(local_feeds)
    for src in FEED_SOURCES:
        if not src.enabled:
            print(f"  - {src.id}: disabled, skipping")
            continue
        entries.extend(ingest_source(fetcher, src, now=now))

    print("Ranking entries (F6)...")
    apply_ranking(entries, now=now)

    print("Building facets (F4 support)...")
    facets = build_facets(entries)

    strip_internal(entries)
    entries.sort(key=lambda e: (-e.get("rank_score", 0), e.get("title", "")))

    commands = sum(1 for e in entries if e["kind"] == "command")
    resources = len(entries) - commands
    index = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now.isoformat(),
        "counts": {
            "entries": len(entries),
            "commands": commands,
            "resources": resources,
            "sources": len({e["source_id"] for e in entries}),
        },
        "facets": facets,
        "sources": all_source_records(),
        "entries": entries,
    }
    return index

def validate(index: dict, schema_path: Path) -> None:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    jsonschema.validate(index, schema)
    print(" index validates against schema (pass)")

def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Cyber Search index.")
    ap.add_argument("--sample", action="store_true",
                    help="Build offline from bundled sample feeds.")
    ap.add_argument("--local-feeds", type=Path, default=None,
                    help="Build offline from downloaded source files in this "
                         "directory (named <source_id>.<ext>).")
    ap.add_argument("--commands", type=Path, default=DEFAULT_COMMANDS)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pretty", action="store_true", help="Indent the JSON output.")
    ap.add_argument("--no-validate", action="store_true")
    args = ap.parse_args()

    try:
        index = build_index(sample=args.sample, commands_path=args.commands,
                             local_feeds=args.local_feeds)
    except Exception as exc:
        print(f"ERROR: build failed: {exc}", file=sys.stderr)
        return 1

    if not args.no_validate:
        try:
            validate(index, args.schema)
        except jsonschema.ValidationError as exc:
            print(f"ERROR: schema validation failed: {exc.message}", file=sys.stderr)
            return 2

    if index["counts"]["entries"] == 0 and args.out.exists():
        print("WARNING: build produced 0 entries; keeping the existing index.",
              file=sys.stderr)
        return 3

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(index, indent=2 if args.pretty else None, ensure_ascii=False),
        encoding="utf-8",
    )
    size_kb = args.out.stat().st_size / 1024
    print(f"\nWrote {args.out} "
          f"({index['counts']['entries']} entries, {size_kb:.1f} KB)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())