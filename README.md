# Cyber Search

**Team Cyber Fiber** — Final Project

**Team members:** Daniel Lawrence · Andrei Ushakov

Cyber Search is a **web-based cybersecurity learning search engine**. It lets
students search thousands of security and shell commands alongside curated
write-ups and videos, and — for commands — explains every flag and breaks a
usage example down token by token. It runs as a **static site**: a build-time
Python pipeline produces one JSON index, and a dependency-light browser front
end searches it entirely client-side.

---

## Repository layout (submission components)

```
Final_Submission/
├── README.md              ← you are here (whole-project overview + how to run)
├── Report/                ← the written project report
│   └── Cyber_Search_Final_Report.docx
├── Presentation/          ← the slide deck
│   └── Cyber_Search_Presentation.pptx
├── Screenshots/           ← screenshots of the running UI (+ NOTES.md)
├── site/                  ← FRONT END (Daniel)
│   ├── index.html         ·   UI: search, filters, "explain" view, accounts, stars, PDF
│   ├── fuse.min.js        ·   Fuse.js v7.0.0 (MIT), vendored so it runs offline
│   ├── jspdf.umd.min.js   ·   jsPDF v2.5.2 (MIT), vendored for the PDF cheat sheet
│   └── index.json         ·   BUILD OUTPUT the page loads (6,670 entries)
├── schema/                ← integration contract between the two tracks
│   ├── index.schema.json  ·   JSON Schema (draft-07)
│   └── SCHEMA.md          ·   human-readable version of the contract
├── data/                  ← curated command dataset (source of truth)
│   └── commands.json
├── indexer/               ← PIPELINE (Andrei) — see indexer/README.md
│   ├── indexer.py, ingest.py, sources.py, fetch.py, commands.py, ranking.py
│   ├── test_pipeline.py, requirements.txt
│   └── sample_feeds/      ·   bundled feeds for offline builds
└── .github/workflows/
    └── build-index.yml    ← scheduled rebuild + GitHub Pages deploy
```

---

## Running the front end locally

The page loads its data with `fetch("./index.json")`. Browsers **block `fetch`
over `file://`**, so opening `index.html` by double-clicking will show an empty
page. Serve the `site/` folder over HTTP instead — any static server works:

```bash
cd site
python3 -m http.server 8000
# then open http://localhost:8000/  in your browser
```

That's the only step — Fuse.js is vendored locally (`site/fuse.min.js`), so no
internet connection is required to run or search the site. On the deployed
GitHub Pages URL it is already served over HTTP, so it just works.

## Accounts, saved commands & PDF export

Signed-out, the site is fully usable: you can **star** any command (☆ on each
card) and those stars are saved in the browser's `localStorage`, and you can
hit **⤓ PDF** in the header to download your starred commands as a themed
cheat sheet (generated in-browser with the vendored jsPDF — no upload). The
**★ saved** header toggle filters the list to just your starred items.

Signing in adds cloud sync: **Continue with Google** or email/password, backed
by Firebase Auth. Your saved commands are merged with (and stored in) Firestore
under `users/{uid}`, so they follow you across devices. If Firebase can't load
(offline, or no keys configured), the site degrades gracefully to local-only
stars + PDF.

**To point this at your own Firebase project** (the committed one is a demo):
1. Firebase console → create a project → add a Web app; copy the config into
   `window.FIREBASE_CONFIG` near the bottom of `site/index.html`. (Web API keys
   are not secret — they're meant to ship in client code.)
2. Authentication → Sign-in method → enable **Email/Password** and **Google**.
3. Firestore Database → create it, and add a rule so users only touch their own
   document, e.g.:
   ```
   match /users/{uid} {
     allow read, write: if request.auth != null && request.auth.uid == uid;
   }
   ```
4. Authentication → Settings → Authorized domains → add wherever you host it
   (e.g. your `*.github.io` domain) so Google sign-in popups are allowed.

## Building the search index (pipeline)

Full instructions are in [`indexer/README.md`](indexer/README.md). Quick version:

```bash
cd indexer
pip install -r requirements.txt

# Offline build from bundled sample feeds (no network needed):
python indexer.py --sample --pretty --out ../site/index.json

# Verify the pipeline end-to-end:
python test_pipeline.py
```

The committed `site/index.json` is a full production build (6,670 entries from
11 sources) and already validates against `schema/index.schema.json`.

---

## Credits & attribution

- **Fuse.js v7.0.0** — client-side fuzzy search. MIT License, © 2023 Kiro Risk.
  <https://fusejs.io> · vendored at `site/fuse.min.js`.
- **jsPDF v2.5.2** — in-browser PDF generation for the saved-commands cheat
  sheet. MIT License. <https://github.com/parallax/jsPDF> · vendored at
  `site/jspdf.umd.min.js`.
- **Firebase JS SDK v10.12.2** — Authentication (Google + email/password) and
  Firestore for cloud-synced saved commands. Apache-2.0, loaded from Google's
  gstatic CDN. <https://firebase.google.com>.
- **Python libraries** (pipeline): `feedparser`, `requests`, `beautifulsoup4`,
  `lxml`, `jsonschema` — see `indexer/requirements.txt`. Each under its own
  open-source license.
- **Indexed content sources** — we store **metadata only** (title, tags,
  publish date, canonical URL) and always deep-link back to the original author;
  no article or video content is rehosted. Sources include 0xdf, IppSec, the
  Nmap Reference Guide, Linux man pages, Microsoft Learn, curl docs, GNU
  manuals, the OpenSSH manual, tcpdump docs, and gobuster. The full, resolvable
  list ships in the `sources` array of `site/index.json`. See the "Copyright
  posture" section of `indexer/README.md`.
- **AI assistance** — some code and documentation in this project were drafted
  and reviewed with the help of an AI assistant (Claude). All output was
  reviewed, tested, and edited by the team.
