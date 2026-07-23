# Delphi
AI Science Officer

## What is this?

A minimalist, SHL-branded news brief viewer with **two interface styles**, each viewable in **two device layouts** — four combinations total, switched instantly with two independent toggles in the header.

**Interface style** (`Cards` / `Headlines`):
- **Cards** — the original Inshorts-style experience. One story at a time, shown as a full-bleed card (image, title, description, "Read more") that you page through with a **Next** button, swipe, mouse wheel, or arrow keys.
- **Headlines** — a Hacker News-style scannable list. All stories at once, each as a numbered row with a linked title, source domain, and a one-line description — built for someone (e.g. a CXO) who wants to scan many headlines quickly rather than swipe through them one by one. There are no images in this view — only Cards shows images.

**Device layout** (`Web` / `Mobile`):
- **Web** — the current view fills a wide panel on the page.
- **Mobile** — the whole screen turns black and the current view is shown inside a phone-shaped mockup (notch, rounded bezel) centered on the page, simulating how it'd look on a phone.

Every story — in either interface style — has a **thumbs up / thumbs down** review control, so you can react to it. A reaction is saved per-story in the browser's `localStorage` (so it survives a page reload) and stays in sync between Cards and Headlines — react to a story in one view, switch to the other, and the same reaction is already reflected there.

It's a static site — plain HTML/CSS/JS, no build step, no backend, no dependencies.

## What's been done

**Phase 1 — Cards + Web/Mobile**
- Built the full front end from scratch: [index.html](index.html), [styles.css](styles.css), [script.js](script.js).
- Theme colors (`#78D64B` green, `#4A4A4A` grey) were sampled directly from `assets/shl-logo.png` to match SHL's actual branding.
- Story data is embedded directly in `script.js` (based on `sample_data/stories.json`), with dummy values filled in for the currently-empty `imageURL` / `readmoreURL` fields:
  - Image → `assets/shl-logo.png`
  - Read more link → `https://www.shl.com/careers/`
- Implemented the Inshorts-style card deck: vertical slide transition, segmented progress bar, Next button, plus swipe/wheel/keyboard navigation.
- Implemented the Web/Mobile toggle, including the phone-bezel mockup used in Mobile mode.
- Added the thumbs up/down review control per card, with mutually-exclusive state, toggle-off-on-repeat-click, and persistence via `localStorage`.

**Phase 2 — Headlines interface style**
- Added a second header toggle, **Cards / Headlines**, independent of the existing Web/Mobile toggle, so all four combinations (Cards×Web, Cards×Mobile, Headlines×Web, Headlines×Mobile) work.
- Built the Headlines view: a scrollable, numbered list in the same green/white SHL theme as Cards, with no images — title (linked to "Read more"), source domain, a short description, and the same thumbs up/down control.
- Refactored the reaction system so a story's thumbs up/down state is shared between however many places it's rendered (Cards and Headlines both exist in the DOM at once) — reacting in one view updates the other immediately.
- Verified end-to-end in a real headless Chromium session across all four view combinations, plus reaction-state sync and `localStorage` persistence — no console errors.

**Phase 3 — Hypothesis Agent backend + live feed**
- Built [hypothesis_agent/](hypothesis_agent/) — an autonomous AI agent (LangGraph search loop, plugin-based architecture) that discovers a single high-value organizational hypothesis and emits a structured package. See [hypothesis_agent/docs/ARCHITECTURE.md](hypothesis_agent/docs/ARCHITECTURE.md) for the full design.
- Wired that agent to *this* frontend: `sample_data/stories.json` is no longer dummy tech-news data — it's the live, growing hypothesis feed, extended with `reaction: "none" | "up" | "down"` and enough fields (lens, scorecard, critique) to render a full "read more" detail page per hypothesis.
- Added a small local API (`hypothesis_agent.server`, FastAPI on `:8200`) that serves the feed, accepts reactions, and can trigger a new hypothesis on demand — plus a **"+ Generate hypothesis"** button in the header that calls it directly.
- `script.js` now fetches the feed live and posts reactions to the API (falling back to a small embedded story deck if the API isn't running, so the page still works standalone).
- The agent guarantees a newly generated hypothesis is never a near-duplicate of one already in the feed (deterministic embedding-similarity check, hard-discarded regardless of score), and softly favors lenses/categories the feed has more thumbs-up on — without ever fully excluding a category.
- Verified end-to-end in a real headless Chromium session: generate → appears in feed → react → persists across reload → read more → detail page renders scorecard + critique. No console errors.

**Phase 4 — the downstream Investigation Pipeline**
- Built [insight_pipeline/](insight_pipeline/) per [docs/PLATFORM_ARCHITECTURE.md](docs/PLATFORM_ARCHITECTURE.md): turns a `HypothesisPackage` into a full executive `InsightPackage` — Investigation Planner → Data Retrieval → Analytics → Root Cause Discovery → Business Insight → Narrative → Visualization Planner → Plot Generation. The Hypothesis Agent stays completely independent of all of it (depended *on*, never the reverse).
- Real, not mocked, where it counts: 4 statistical methods (correlation, regression, ANOVA, chi-square) run real `scipy` against real `Book1.xlsx` rows; 5 chart types render real `matplotlib` PNGs; every LLM-reasoned stage (planning, root-cause, business insight, narrative, visualization selection) is offline-testable via `MockLLMService` and was also run end to end against the real SHL LiteLLM endpoint.
- One live run genuinely caught its own analysis's weak spot: the Investigation Planner asked for constructs the real cohort data doesn't literally have, and rather than fabricating a conclusion, Root Cause/Business Insight correctly flagged the data-model mismatch as the actual finding — a legitimate example of the "internal critic" philosophy carrying through the whole pipeline, not just the Hypothesis Agent.
- 86 tests passing across both packages (`hypothesis_agent` + `insight_pipeline`), including an architecture-boundary test enforcing that contracts/ports never import `pandas`/`matplotlib`/etc. and that `hypothesis_agent` never imports `insight_pipeline`.

## Project structure

```
Delphi/
├── index.html          # page structure (header, both toggles, card viewport, headline list)
├── styles.css           # SHL theme, web/mobile layouts, card styles, headline-list styles
├── script.js             # live feed fetch + card/headline rendering, navigation, toggles, reactions
├── assets/
│   └── shl-logo.png     # SHL logo — used in the header and as the fallback card image
├── sample_data/
│   ├── stories.json      # THE LIVE HYPOTHESIS FEED — starts as [], grows as you generate
│   ├── hypotheses/       # generated "read more" detail pages, one per hypothesis (gitignored content)
│   └── insights/figures/ # generated report charts, one per InsightPackage (gitignored content)
├── docs/
│   └── PLATFORM_ARCHITECTURE.md   # design for the full multi-agent platform
├── hypothesis_agent/    # the autonomous Hypothesis Agent — see its own README + docs/ARCHITECTURE.md
├── insight_pipeline/    # HypothesisPackage -> InsightPackage pipeline — see its own README
└── README.md
```

## Running it locally

No install, no build — just serve the folder and open it in Chrome or Edge.

### Option A — serve it (recommended)

From the parent directory (one level above `Delphi/`):

```bash
cd ~/AI-Thon/Delphie?
python3 -m http.server 8100
```

Then open:

```
http://localhost:8100/Delphi/
```

> Note the `/Delphi/` in the URL — `http.server` serves whatever directory you ran it from, and here that's the parent folder, not `Delphi/` itself.

If you'd rather not deal with the path, `cd` straight into the app folder instead and drop the `/Delphi/` suffix:

```bash
cd ~/AI-Thon/Delphie?/Delphi
python3 -m http.server 8100
```
then open `http://localhost:8100/`.

Stop the server with `Ctrl+C` in that terminal.

### Option B — open the file directly

Double-click `index.html`, or:

```bash
xdg-open "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/index.html"   # Linux
open "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/index.html"        # macOS
```

This still works fully offline — if the Hypothesis Agent API (below) isn't running, the page falls back to a small embedded story deck instead of the live feed, so there's no CORS issue from opening via `file://`.

## Running the complete project

The full system is **three independent processes**, each in its own
terminal, plus a one-time setup pass. Nothing auto-starts anything else —
if a piece isn't running, its part of the loop just won't work (the
frontend falls back to an offline demo deck; the Investigation Pipeline
simply has no `HypothesisPackage` to work from).

| # | Terminal | Command | Port | Required for |
|---|---|---|---|---|
| 1 | Static frontend | `python3 -m http.server 8100` | 8100 | Viewing the site at all |
| 2 | Hypothesis Agent API | `python -m hypothesis_agent.server` | 8200 | The live feed / "+ Generate hypothesis" button |
| 3 | Investigation Pipeline API | `python -m insight_pipeline.server` | 8300 | Turning a hypothesis into a full analytics/root-cause/narrative/chart report (not yet wired into the UI — call it directly, see below) |

### One-time setup (run once, in any terminal)

```bash
cd ~/AI-Thon/Delphie?/Delphi

# --- Hypothesis Agent ---
cd hypothesis_agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[server,llm-litellm,sample-data]"
cp .env.example .env   # then fill in LITELLM_API_KEY — everything else is pre-filled
deactivate
cd ..

# --- Investigation Pipeline (depends on hypothesis_agent above) ---
cd insight_pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../hypothesis_agent
pip install -e ".[dev,analytics,plotting,data-excel,server]"
deactivate
cd ..
```

`hypothesis_agent/.env` already points at the SHL internal LiteLLM endpoint
(`https://labs.shl.com/llm-internal/`) and activates it
(`HYPOTHESIS_AGENT__BACKENDS__LLM=litellm`) — the key is the only thing you
need to add. `insight_pipeline` reuses that same `.env` (no separate key).
Both packages' own test suites and offline demo scripts always force the
offline `MockLLMService` regardless of `.env`, so `pytest` and
`examples/*.py` keep working with zero setup either way — only the two
servers use whatever `.env` says.

### Terminal 1 — static frontend

```bash
cd ~/AI-Thon/Delphie?/Delphi
python3 -m http.server 8100
```
Open `http://localhost:8100/`.

### Terminal 2 — Hypothesis Agent API

```bash
source ~/AI-Thon/Delphie?/Delphi/hypothesis_agent/.venv/bin/activate
python -m hypothesis_agent.server
```
(Data paths like `sample_data/` are anchored to the repo root internally,
so this works from any starting directory — only the venv needs activating.)
Serves on `http://127.0.0.1:8200`. `sample_data/stories.json` starts as
`[]` — nothing's been generated yet. With terminals 1 and 2 running, click
**"+ Generate hypothesis"** in the header: a new card appears; reacting
👍/👎 persists to `sample_data/stories.json` (not just the browser);
**Read more** opens a generated detail page with the full mechanism,
scorecard, and critique.

### Terminal 3 — Investigation Pipeline API

```bash
source ~/AI-Thon/Delphie?/Delphi/insight_pipeline/.venv/bin/activate
python -m insight_pipeline.server
```
(same as terminal 2 — `Book1.xlsx` and `sample_data/` resolve to the repo
root regardless of the starting directory.)
Serves on `http://127.0.0.1:8300`. Turns one `HypothesisPackage` (e.g. one
entry already in `sample_data/stories.json`, generated via terminal 2) into
a full `InsightPackage`: an investigation plan, real statistical analysis,
a root-cause graph, business findings/risks/recommendations, an executive
narrative, and rendered chart PNGs under `sample_data/insights/figures/`.
There's no frontend button for this yet — from a fourth terminal (with
terminals 2 and 3 both already running, and at least one hypothesis
already generated via terminal 2's "+ Generate hypothesis" button), run:

```bash
cd ~/AI-Thon/Delphie?/Delphi/insight_pipeline && source .venv/bin/activate
python examples/run_investigation_from_server.py
```

This fetches the most recent hypothesis from terminal 2's API and POSTs it
to terminal 3's API. Real, non-mocked results take a few minutes (many
real LLM calls). `GET /api/insights` lists past reports,
`GET /api/insights/{id}` returns one in full.

See [hypothesis_agent/docs/ARCHITECTURE.md §18](hypothesis_agent/docs/ARCHITECTURE.md#18-frontend-integration-the-live-json-feed--local-api-server)
for how the Hypothesis Agent + frontend fit together (§11.1 for the
dedup/soft-bias guarantees), and
[docs/PLATFORM_ARCHITECTURE.md](docs/PLATFORM_ARCHITECTURE.md) for the full
Investigation Pipeline design.

## Using the app

| Action | How |
|---|---|
| Switch interface style | Click **Cards** / **Headlines** in the top-right toggle |
| Switch device layout | Click **Web** / **Mobile** in the top-right toggle |
| Next card *(Cards view)* | Click the green ⌄ button, swipe up, scroll down, or press `↓` / `Space` |
| Previous card *(Cards view)* | Swipe down, scroll up, or press `↑` |
| Open full story | Click the title (**Headlines**) or **Read more** (**Cards**) — opens the generated hypothesis detail page |
| React to a story | Click 👍 or 👎 next to the story (click again to undo) — synced across both interface styles, and persisted server-side via the Hypothesis Agent API if it's running |
| Generate a new hypothesis | Click **"+ Generate hypothesis"** in the header (requires the API running — see above) |

## Customizing

- **Hypothesis content**: not hand-edited — it's generated by [hypothesis_agent](hypothesis_agent/). To change *what kind* of hypotheses come out, edit its business lens catalog, prompts, or scoring weights (see its `docs/ARCHITECTURE.md`), not this frontend.
- **Offline fallback deck**: `FALLBACK_STORIES` at the top of [script.js](script.js) — shown only when the API is unreachable.
- **Fallback image/link**: `DUMMY_IMAGE` / `DUMMY_URL` at the top of [script.js](script.js), used by the fallback deck and for any entry missing an image.
- **Colors**: all theme colors are CSS custom properties at the top of [styles.css](styles.css) (`:root`).
