# Delphi — an AI Science Officer

*AI-thon submission — theme: Data and Insights.*

Delphi is a long-running AI research agent for people analytics. It replaces the
one-off, analyst-limited engagement model — where a client's assessment data is
studied once, a deck is delivered, and the engagement ends — with a continuous
loop that **autonomously forms hypotheses about an organization, tests them
against that client's own SHL assessment data, and turns each result into a
short, striking artifact a stakeholder can judge in seconds.**

It does not just suggest ideas in words — it runs its own statistics inside a
walled-off environment and reports what the data actually shows. Every
downstream insight is **grounded in real SHL metrics** (OPQ / GSA / MQ / 360 /
HiPo / Leader-Challenges) and the client's real columns — the system is
structurally incapable of inventing a metric — so conclusions are personalized
to the client's context instead of a shared template.

The name comes from the **Delphi method**: reaching a conclusion through several
rounds of expert feedback. Here, artifacts are reviewed over rounds by two
groups — senior client stakeholders (*is this useful?*) and SHL IO psychologists
(*is this valid?*) — and nothing counts as validated until it passes both.
Insights are at the **organization and team level**, never about individual
employees.

**Why it matters for SHL:** it moves revenue from one-time projects toward
continuous engagement, extracts far more value from data clients already hold,
and scales SHL's science past the capacity of individual human analysts — while
keeping human experts as the quality bar.

---

## What's actually built in this repo

The vision above is realized as a **two-stage, offline-testable pipeline** plus a
lightweight frontend feed:

| Stage | Package | What it does |
|---|---|---|
| **1. Hypothesis Agent** | [`hypothesis_agent/`](.) *(this package)* | A LangGraph search loop that creatively discovers **one** high-value, non-obvious organizational hypothesis and emits a structured `HypothesisPackage`. Sees only the data *schema*, never row values. |
| **2. Investigation Pipeline** | [`../insight_pipeline/`](../insight_pipeline/) | Turns that hypothesis into a full executive `InsightPackage`: grounds every construct to real columns → plans the investigation → retrieves data → runs real `scipy` analytics → root-cause → business insight → narrative → real `matplotlib` charts → a single CXO-grade HTML report. |
| **Frontend** | [`../index.html`](../index.html), [`../insight.html`](../insight.html) | An SHL-branded feed (Cards / Headlines views) of generated hypotheses, each opening into its full grounded insight report. |

The **grounding boundary** is the core scientific guarantee: hypothesis
generation is free to be creative, but everything downstream may only reason with
real SHL metrics and the organization's actually-present columns — a construct
with no real-data proxy is reported honestly as unmeasurable, never fabricated
into a fake variable or a data-free causal edge.

The Hypothesis Agent stays completely independent of the Investigation Pipeline
(depended *on*, never the reverse), and both run fully offline out of the box
via `MockLLMService` / `HashEmbeddingService` — zero network, zero API keys — so
the whole system is testable without any live infrastructure.

---

## Running Delphi end-to-end

The full system is **three long-running processes** (frontend + two APIs), plus
an optional command to drive one investigation. Everything is anchored to the
repo root: `Delphi/`.

> **Path note:** the repo lives under a directory literally named `Delphie?` (the
> `?` is part of the folder name), so **always quote the path** in a shell —
> `cd "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi"`. Adjust the base path if
> you cloned it elsewhere.

### One-time setup (run once)

Two independent virtualenvs — one per package (`insight_pipeline` depends on
`hypothesis_agent`, never the reverse):

```bash
cd "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi"

# --- Hypothesis Agent (port 8200) ---
cd hypothesis_agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[server,llm-litellm,sample-data,observability]"
cp .env.example .env      # then edit .env and fill in LITELLM_API_KEY (see below)
deactivate
cd ..

# --- Investigation Pipeline (port 8300) ---
cd insight_pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -e "../hypothesis_agent[llm-litellm,observability]"
pip install -e ".[dev,analytics,plotting,data-excel,server]"
deactivate
cd ..
```

**API key:** `hypothesis_agent/.env` is pre-pointed at the SHL internal LiteLLM
endpoint (`https://labs.shl.com/llm-internal/`) and pre-activated
(`HYPOTHESIS_AGENT__BACKENDS__LLM=litellm`). The **only** thing you must add is
`LITELLM_API_KEY=...`. `insight_pipeline` reuses this same `.env` — no second
key. (Both packages' test suites and demo scripts force the offline
`MockLLMService` regardless of `.env`, so `pytest` and the `examples/*.py`
scripts always work with zero setup; only the two servers use the real key.)

The database is `Book1_standardized.xlsx` at the repo root (402 candidates × 235
SHL assessment + HR-outcome columns) — already present, nothing to configure.

### The three processes

Open three terminals. Each command is self-contained; paths resolve to the repo
root internally, so only the venv needs activating.

**Terminal 1 — static frontend (port 8100):**
```bash
cd "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi"
python3 -m http.server 8100
```
Then open **http://localhost:8100/** in Chrome/Edge.

**Terminal 2 — Hypothesis Agent API (port 8200):**
```bash
source "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/hypothesis_agent/.venv/bin/activate"
python -m hypothesis_agent.server
```
Powers the live feed and the **"+ Generate hypothesis"** button. Serves
`GET /api/stories`, `POST /api/stories/{id}/reaction`, `POST /api/generate`.

**Terminal 3 — Investigation Pipeline API (port 8300):**
```bash
source "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/insight_pipeline/.venv/bin/activate"
python -m insight_pipeline.server
```
Turns a hypothesis into a full `InsightPackage` (analytics + root-cause +
narrative + rendered chart PNGs under `sample_data/insights/figures/`). Serves
`POST /api/investigate`, `GET /api/insights`, `GET /api/insights/{id}`.

### Driving it

With all three running, in the browser at **http://localhost:8100/**:

1. Click **"+ Generate hypothesis"** in the header. The Hypothesis Agent
   generates a new hypothesis (a card appears in the feed), then the frontend
   automatically runs it through the Investigation Pipeline. A real, non-mocked
   run makes several LLM calls plus real analytics/plotting, so it can take a few
   minutes.
2. React 👍/👎 on any card — persists server-side.
3. Click **Read more** on an investigated card to open its full grounded insight
   report at `insight.html?id=<insight_id>`.

**Optional — Terminal 4, drive one investigation from the CLI** (instead of the
UI button; needs Terminals 2 & 3 running and at least one hypothesis already
generated):
```bash
cd "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/insight_pipeline"
source .venv/bin/activate
python examples/run_investigation_from_server.py
```
It fetches the most recent hypothesis from Terminal 2 and POSTs it to Terminal 3.

### Fully offline (no API key, no servers)

To see each stage run end-to-end against the real cohort data with **zero setup**
(mock LLM, real `scipy`/`matplotlib`):
```bash
cd "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/insight_pipeline"
source .venv/bin/activate
python examples/run_investigation_demo.py   # Hypothesis Agent -> full InsightPackage, offline
```

### Run the tests

```bash
cd "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/hypothesis_agent" && source .venv/bin/activate && pytest -q && deactivate
cd "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/insight_pipeline"  && source .venv/bin/activate && pytest -q && deactivate
```
All tests are offline (mock LLM), no keys required.

---

## This package — the Hypothesis Agent (in detail)

The first stage of Delphi. Given an organization, it autonomously searches the
space of possible organizational hypotheses and emits **one** high-value,
non-obvious, structured hypothesis — a `HypothesisPackage` — for the downstream
Investigation Pipeline to consume. It does not analyze data, run statistics, or
talk to end users; see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full
design.

Every external dependency — data sources, memory, embeddings, LLMs, feedback,
downstream agents — sits behind an interface (`ports/`) with a swappable adapter
(`adapters/`). The reference adapters are in-memory and offline (`MockLLMService`,
`HashEmbeddingService`) so the whole thing runs with zero network access and zero
API keys, out of the box.

### Quickstart (this package only, offline)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python examples/run_local_demo.py   # full search loop, offline, no config needed
pytest                              # unit + integration tests, offline
```

### Using a real LLM

`.env` (gitignored, loaded automatically via `python-dotenv` whenever
`di/container.py` is imported, regardless of cwd) is already set up for the SHL
internal LiteLLM endpoint:

```bash
pip install -e ".[llm-litellm]"
```
```dotenv
# .env
HYPOTHESIS_AGENT__BACKENDS__LLM=litellm
LITELLM_API_BASE=https://labs.shl.com/llm-internal/
LITELLM_API_KEY=          # <- add your key
```

That's the only thing you need to fill in — `backends.llm` and the endpoint are
already active. `examples/run_local_demo.py` and the test suite ignore this and
force `MockLLMService` explicitly in code either way, so they stay offline
regardless of what's in `.env`; `hypothesis_agent.server` and any direct
`HypothesisAgent`/`build_dependencies()` use pick it up. If the endpoint expects
a specific model identifier (it may need an `openai/` prefix or a
gateway-specific name), also set `HYPOTHESIS_AGENT__LLM__MODEL` — the default
(`gpt-4.1-nano`) is a generic OpenAI-compatible guess, not guaranteed to match
your gateway's naming.

To revert to the offline mock: comment out `HYPOTHESIS_AGENT__BACKENDS__LLM` in
`.env`, or set it to `mock`.

**OpenAI directly** (alternative to LiteLLM):
```bash
pip install -e ".[llm-openai]"
# in .env: OPENAI_API_KEY=...
```
Then set `backends.llm: openai` and `backends.embedding: openai`.

### Running the live JSON-backed feed + local API

The Delphi frontend (`../index.html`) can display a *live*, growing feed of
generated hypotheses instead of the offline demo — see
[Running Delphi end-to-end](#running-delphi-end-to-end) above for the full
walkthrough; in short:

```bash
pip install -e ".[server]"
cd ..                          # the Delphi/ repo root — the server resolves
python -m hypothesis_agent.server   # sample_data/stories.json relative to cwd
```

This forces `historical_memory_repository`/`feedback_repository` to `json_file`
(`JsonHypothesisStore`, §11.1 of the architecture doc) regardless of other
config, and exposes `GET /api/stories`, `POST /api/stories/{id}/reaction`, and
`POST /api/generate` on `:8200`.

### Optional extras

| Extra | Enables | Notes |
|---|---|---|
| `llm-openai` | `OpenAILLMService`, `OpenAIEmbeddingService` | needs `OPENAI_API_KEY` |
| `llm-litellm` | `LiteLLMService` | needs `LITELLM_API_KEY` (+ `LITELLM_API_BASE` for a proxy) |
| `deep-agents` | `DeepAgentUnderstandingEngine` | requires Python ≥3.11 |
| `strands` | `StrandsCriticOrchestrator` | needs a configured Strands model provider |
| `server` | `hypothesis_agent.server` (FastAPI + uvicorn) | powers the live JSON-backed feed |

### Layout

See [docs/ARCHITECTURE.md §6](docs/ARCHITECTURE.md#6-repository-folder-structure)
for the full annotated repository structure and every other design section
(component diagrams, LangGraph state graph, class diagram, data contracts,
prompt/memory/search architecture, testing strategy, and the implementation
roadmap).
