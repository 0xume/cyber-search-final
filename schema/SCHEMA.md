# Cyber Search — Index Schema (Integration Contract)

This document is the human-readable companion to
[`index.schema.json`](index.schema.json) (JSON Schema draft-07). It is the
**contract between the two tracks**: the build-time Python pipeline (Andrei)
produces a file that conforms to this shape, and the client-side front end
(Daniel) consumes it. Any change here must be agreed by both team members and
reflected in `index.schema.json`, which is validated in CI on every push.

Current `schema_version`: **1.0.0** (semantic versioning; the front end checks
the major version on load).

---

## Top-level object

The index is a single JSON object. `site/index.json` is the build output the
browser loads at runtime.

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `schema_version` | string `"MAJOR.MINOR.PATCH"` | yes | Version of this contract. |
| `generated_at` | ISO-8601 date-time (UTC) | yes | When the index was built. |
| `counts` | object | yes | Precomputed totals so the UI shows stats without scanning `entries`. |
| `facets` | object | yes | Precomputed filter buckets with counts (powers Daniel's filter UI, F4). |
| `sources` | array of `source` | no | Distinct sources that contributed, for attribution / the "about" view. |
| `entries` | array of `entry` | yes | The searchable items. |

`additionalProperties` is `false` at every level — unknown keys are rejected by
validation, which keeps both tracks honest.

### `counts`

```json
{ "entries": 6670, "commands": 6127, "resources": 543, "sources": 11 }
```

All four keys are required, non-negative integers.

### `facets`

An object with optional buckets for `categories`, `tags`, `os`, `difficulty`,
and `kind`. Each bucket is an array of `{ "value": string, "count": integer }`,
so the front end can render filter chips (and their counts) without a full pass
over `entries`.

---

## `source`

```json
{
  "id": "ippsec",
  "name": "IppSec",
  "author": "IppSec",
  "homepage": "https://ippsec.rocks/",
  "kind": "writeups",
  "license_note": "Metadata only (title, tags, URL). Content is not rehosted; every result links back to the original author."
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string, `^[a-z0-9_-]+$` | yes | Stable slug; `entry.source_id` references this. |
| `name` | string | yes | Human-readable name. |
| `author` | string | no | Content creator, where one is credited. |
| `homepage` | URI | no | |
| `kind` | enum | yes | `writeups` \| `reference` \| `docs` \| `manpages` \| `curated`. |
| `license_note` | string | no | How the material may be used. We store metadata only and always deep-link back. |

---

## `entry`

The core searchable unit. Two kinds share one shape:

- **`command`** — curated reference cards (features F2 / F8). Always carry a
  `command` detail object.
- **`resource`** — write-ups / videos ingested from feeds and sitemaps
  (feature F3). Metadata only; the body is never stored.

```json
{
  "id": "cmd:nmap",
  "kind": "command",
  "title": "nmap — network mapper / port scanner",
  "summary": "Scan hosts and networks to discover open ports and services.",
  "url": "https://nmap.org/book/man.html",
  "source_id": "nmap-docs",
  "tags": ["scanning", "recon", "ports"],
  "categories": ["scanning"],
  "os": ["cross-platform"],
  "difficulty": "beginner",
  "keywords": ["portscan", "service detection"],
  "rank_score": 0.94,
  "indexed_at": "2026-07-07T00:03:00Z",
  "command": { "...": "see command_detail" }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string, `^(cmd\|res):[a-z0-9._-]+$` | yes | Globally unique; `cmd:` for commands, `res:` for resources. |
| `kind` | `"command"` \| `"resource"` | yes | |
| `title` | string (min length 1) | yes | |
| `summary` | string | yes | One/two plain-language sentences ("what it does"). |
| `url` | URI | yes | Deep link back to the original (F6). The app never rehosts content. |
| `source_id` | string | yes | References a `source.id`. |
| `tags` | string[] | yes | Free-form; used by faceted filtering and search. |
| `categories` | enum[] | yes | Controlled vocabulary (see below) so filter chips are consistent. |
| `os` | enum[] | yes | `linux` \| `windows` \| `macos` \| `cross-platform`. |
| `difficulty` | enum | yes | `beginner` \| `intermediate` \| `advanced`. |
| `keywords` | string[] | yes | Extra searchable terms (aliases, related tools) to boost fuzzy matching. |
| `rank_score` | number ≥ 0 | yes | Precomputed relevance weight (F6); tie-breaker when Fuse.js scores are equal. |
| `indexed_at` | ISO-8601 date-time | yes | |
| `command` | `command_detail` | only if `kind == "command"` | Powers the "Explain the Command" view (F8). |

**`categories` controlled vocabulary:** `reconnaissance`, `scanning`,
`enumeration`, `dns`, `networking`, `web`, `transfer`, `remote-access`,
`traffic-analysis`, `brute-force`, `cryptography`, `forensics`, `general`.

---

## `command_detail` (present only on command entries)

```json
{
  "tool": "nmap",
  "synopsis": "nmap [scan type] [options] {target}",
  "platforms": ["linux", "windows", "macos"],
  "flags": [
    { "flag": "-sV", "meaning": "Probe open ports to determine service/version info." },
    { "flag": "-p", "arg": "<ports>", "meaning": "Only scan the specified ports." }
  ],
  "examples": [
    {
      "command": "nmap -sV -p 1-1000 10.10.10.5",
      "explanation": "Version-scan the first 1000 ports of a host.",
      "breakdown": [
        { "token": "nmap", "role": "the port scanner" },
        { "token": "-sV", "role": "detect service versions" },
        { "token": "-p 1-1000", "role": "limit to ports 1–1000" },
        { "token": "10.10.10.5", "role": "the target host" }
      ]
    }
  ],
  "see_also": ["masscan", "rustscan"]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `tool` | string | yes | Binary/tool name. |
| `synopsis` | string | yes | Canonical usage line. |
| `platforms` | enum[] | no | `linux` \| `windows` \| `macos`. |
| `flags` | array | yes | Each: `{ flag, arg?, meaning }` — the educational "why". |
| `examples` | array (min 1) | yes | Each: `{ command, explanation, breakdown? }`. |
| `examples[].breakdown` | array | no | `{ token, role }` pairs that drive the token-by-token F8 view. |
| `see_also` | string[] | no | Related tools, for cross-navigation. |

---

## Validation

The pipeline validates the whole index against `index.schema.json` before
writing, and CI re-validates on every push and on the daily rebuild. To check a
build by hand:

```bash
python - <<'PY'
import json, jsonschema
schema = json.load(open("schema/index.schema.json"))
index  = json.load(open("site/index.json"))
jsonschema.validate(index, schema)
print("index validates:", len(index["entries"]), "entries")
PY
```
