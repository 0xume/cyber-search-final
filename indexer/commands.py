from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-")

def load_command_entries(commands_path: Path, *, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    raw = json.loads(Path(commands_path).read_text(encoding="utf-8"))
    entries: list[dict] = []

    for card in raw.get("commands", []):
        tool = card["tool"]
        entry_id = f"cmd:{_slug(tool)}"

        keywords = list(dict.fromkeys(
            card.get("keywords", []) + card.get("see_also", []) + [tool]
        ))

        command_detail = {
            "tool": tool,
            "synopsis": card["synopsis"],
            "platforms": [os_ for os_ in card.get("os", []) if os_ in ("linux", "windows", "macos")],
            "flags": card.get("flags", []),
            "examples": card.get("examples", []),
        }
        if card.get("see_also"):
            command_detail["see_also"] = card["see_also"]

        entry = {
            "id": entry_id,
            "kind": "command",
            "title": card.get("title", tool),
            "summary": card["summary"],
            "url": card["url"],
            "source_id": card["source_id"],
            "tags": card.get("tags", []),
            "categories": card.get("categories", []),
            "os": card.get("os", []),
            "difficulty": card.get("difficulty", "beginner"),
            "keywords": keywords,
            "indexed_at": now.isoformat(),
            "command": command_detail,
            "_published": None,
        }
        entries.append(entry)

    return entries