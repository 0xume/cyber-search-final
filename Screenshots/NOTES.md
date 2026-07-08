# Screenshots

Captured from the running front end (`site/index.html`) served locally against
the full production index (`site/index.json`, 6,670 entries). To reproduce, see
"Running the front end locally" in the top-level `README.md`.

| File | What it shows |
|------|---------------|
| `01_home_dark.png` | Landing page in the default midnight-ops dark theme: search bar, faceted filter rail (categories / tags / OS / difficulty / kind), and ranked command cards. |
| `02_search_results.png` | Live fuzzy search for **"zone transfer"** — Fuse.js matches across titles, tags, and keywords; results are ordered by relevance with `rank_score` as the tie-breaker. |
| `03_explain_modal.png` | The **"Explain the Command"** modal (feature F8): token-by-token breakdown of a command, per-flag plain-language meanings, and copy-to-clipboard buttons on each example. |
| `04_light_theme_filters.png` | Light ("day") theme toggle active, filtered search for **"nmap"**. |

## Accounts, stars & PDF (added)

| File | What it shows |
|------|---------------|
| `05_saved_stars.png` | Command cards with the ★ save control (two starred); header shows the **★ saved** count, **⤓ PDF** export, and the **sign in** button. |
| `06_sign_in_modal.png` | The account modal in the site's theme: **Continue with Google** plus email/password sign-in, backed by Firebase Auth. |
| `07_saved_only_view.png` | The **★ saved** header toggle active, filtering results down to just the starred commands. |
