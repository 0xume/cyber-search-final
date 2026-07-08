#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

from indexer import build_index, DEFAULT_COMMANDS, DEFAULT_SCHEMA

FAILS: list[str] = []

def check(cond: bool, msg: str) -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {msg}")
    if not cond:
        FAILS.append(msg)

def main() -> int:
    print("Building sample index...")
    index = build_index(sample=True, commands_path=DEFAULT_COMMANDS)
    entries = index["entries"]

    print("\nSchema:")
    schema = json.loads(Path(DEFAULT_SCHEMA).read_text())
    try:
        jsonschema.validate(index, schema)
        check(True, "index validates against schema")
    except jsonschema.ValidationError as exc:
        check(False, f"schema validation: {exc.message}")

    print("\nStructure:")
    check(index["counts"]["entries"] == len(entries), "counts.entries matches array length")
    check(index["counts"]["commands"] > 0, "has at least one command entry")
    check(index["counts"]["resources"] > 0, "has at least one resource entry")

    ids = [e["id"] for e in entries]
    check(len(ids) == len(set(ids)), "all entry ids are unique")

    print("\nCommand cards (F2/F8):")
    cmds = [e for e in entries if e["kind"] == "command"]
    check(all("command" in e for e in cmds), "every command entry has a 'command' block")
    check(all(e["command"]["examples"] for e in cmds), "every command has >=1 example")
    with_breakdown = [e for e in cmds
                      if any(ex.get("breakdown") for ex in e["command"]["examples"])]
    check(len(with_breakdown) == len(cmds), "every command has an F8 token breakdown")
    for tool in ("nmap", "dig", "netstat"):
        check(any(e["id"] == f"cmd:{tool}" for e in cmds), f"'{tool}' card present (named in proposal)")

    print("\nAttribution (F6):")
    source_ids = {s["id"] for s in index["sources"]}
    check(all(e["source_id"] in source_ids for e in entries),
          "every entry.source_id resolves to a known source")
    check(all(e["url"].startswith(("http://", "https://")) for e in entries),
          "every entry deep-links to an http(s) source")

    print("\nRanking (F6):")
    check(all(isinstance(e["rank_score"], (int, float)) and e["rank_score"] >= 0
              for e in entries), "every entry has a non-negative rank_score")
    scores = [e["rank_score"] for e in entries]
    check(scores == sorted(scores, reverse=True), "entries are pre-sorted by rank_score desc")

    print("\nFacets (F4 support):")
    for key in ("categories", "tags", "os", "difficulty", "kind"):
        check(key in index["facets"], f"facet '{key}' present")

    print("\nInternal fields stripped:")
    check(all(not any(k.startswith("_") for k in e) for e in entries),
          "no internal (_-prefixed) keys leak into output")

    print(f"\n{'ALL CHECKS PASSED' if not FAILS else str(len(FAILS)) + ' CHECK(S) FAILED'}")
    return 1 if FAILS else 0

if __name__ == "__main__":
    sys.exit(main())