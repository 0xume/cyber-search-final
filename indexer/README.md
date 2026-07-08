> **Pipeline track (Andrei Ushakov).** This document covers the data pipeline and deployment half of the project. For the whole-project overview, team, and how to run the front end, see the [top-level README](../README.md). Paths below are relative to the repository root.

# Cyber Search — Data Pipeline & Deployment

This is **Andrei Ushakov's** track for the Cyber Search final project
(Team Cyber Fiber). It builds the search index that the front end consumes and
deploys the static site.

Covers the proposal responsibilities:

| Item | Where |
|------|-------|
| F2 — Curated command reference dataset | [`data/commands.json`](data/commands.json) + [`indexer/commands.py`](indexer/commands.py) |
| F3 — Multi-source indexing pipeline | [`indexer/ingest.py`](indexer/ingest.py), [`indexer/sources.py`](indexer/sources.py) |
| F6 — Deep-link attribution + relevance ranking | attribution throughout; ranking in [`indexer/ranking.py`](indexer/ranking.py) |
| JSON schema (integration contract) | [`schema/index.schema.json`](schema/index.schema.json), [`schema/SCHEMA.md`](schema/SCHEMA.md) |
| Deployment (GitHub Pages + Actions) | [`.github/workflows/build-index.yml`](.github/workflows/build-index.yml) |

## Layout

```
cyber-search/
├── data/
│   └── commands.json          # F2: curated command cards (source of truth)
├── indexer/
│   ├── indexer.py             # pipeline orchestrator (entry point)
│   ├── sources.py             # source registry + attribution metadata
│   ├── fetch.py               # polite fetcher: robots.txt, delays, caching
│   ├── ingest.py              # F3: feed/sitemap -> resource entries
│   ├── commands.py            # F2: dataset -> command entries (F8 breakdowns)
│   ├── ranking.py             # F6: precomputed rank_score
│   ├── test_pipeline.py       # smoke test (runs in CI)
│   ├── requirements.txt
│   └── sample_feeds/          # bundled feeds for offline builds
├── schema/
│   ├── index.schema.json      # the integration contract (draft-07)
│   └── SCHEMA.md              # human-readable contract for the front end
├── site/
│   └── index.json             # BUILD OUTPUT: what the front end loads
└── .github/workflows/
    └── build-index.yml        # scheduled rebuild + Pages deploy
```

`site/` is also where Daniel's static front end lives — the workflow publishes
that whole directory, so `index.json` sits right next to `index.html`.

## Quick start

```bash
cd indexer
pip install -r requirements.txt

# Offline build from bundled sample feeds — great for developing the front end.
python indexer.py --sample --pretty --out ../site/index.json

# Offline build from manually downloaded sources (named <source_id>.<ext>,
# e.g. 0xdf.xml, ippsec.json, plus optional <source_id>.sitemap.xml).
python indexer.py --local-feeds /path/to/downloads --pretty --out ../site/index.json

# Live build — fetches the real sources (needs network; run outside the sandbox).
python indexer.py --pretty --out ../site/index.json

# Verify everything holds together.
python test_pipeline.py
```

`--sample` is the mode to hand Daniel: it produces a realistic 26-entry index
with zero network access, so both tracks can build in parallel against the same
data (proposal §4, "build in parallel against a small sample index").

## How it works

1. **Command cards (F2).** `data/commands.json` is hand-maintained. Each card
   has a synopsis, flags with plain-language meanings, and worked examples with
   a token-by-token `breakdown` that drives the "Explain the Command" view (F8).
2. **Ingestion (F3).** For each source we read its published machine-readable
   interface — an Atom/RSS feed, a sitemap, or (for ippsec.rocks) its prebuilt
   `dataset.json` — and keep **metadata only** (title, tags, publish date,
   canonical URL). No article bodies are stored. ippsec entries deep-link back
   to the exact YouTube video (or HTB Academy module); a `granularity` option
   on that source switches between one entry per video (default) and one per
   timestamped transcript line.
3. **Full coverage.** A feed only exposes the newest posts (0xdf's Atom feed
   carries ~10). Sources may also declare a `coverage_url` sitemap; the ingester
   merges both — recent posts keep their rich feed tags, and the entire
   back-catalogue is pulled from the sitemap (filtered to real post URLs).
4. **Politeness.** `fetch.py` sends a descriptive User-Agent, honours
   `robots.txt`, spaces out requests per host, and caches responses so a failed
   rebuild falls back to the last good copy rather than emptying the site.
5. **Ranking (F6).** `ranking.py` assigns each entry a transparent `rank_score`
   from completeness and freshness signals. Fuse.js scores query relevance in
   the browser; `rank_score` is the stable tie-breaker.
6. **Attribution (F6).** Every entry carries a `source_id` (resolvable in the
   index's `sources` array) and a `url` that deep-links back to the original.
7. **Validation.** The build validates the whole index against the schema before
   writing. CI runs the smoke test and re-validates on every push and daily.

## Copyright posture

We store titles, tags, and URLs — never the content itself — and always link
back to the author (proposal §6). This keeps the project on the right side of
copyright and sends traffic to the creators. The fetcher only reads interfaces
the sites publish for machines (feeds/sitemaps) and respects `robots.txt`.

## Adding a source

Add a `FeedSource(...)` to `FEED_SOURCES` in `indexer/sources.py` (id, homepage,
feed/sitemap URL, kind). Add a matching sample file under `sample_feeds/` and a
line in `configure_sample_sources()` if you want it in offline builds. Re-run
the smoke test.

## Deployment

`build-index.yml` runs on push, daily at 06:00 UTC, and on manual dispatch. It
installs deps, runs the smoke test, builds the index (falling back to a sample
build if a live fetch yields nothing), re-validates, and deploys `site/` to
GitHub Pages. Enable Pages once in **Settings → Pages → Source: GitHub Actions**.
