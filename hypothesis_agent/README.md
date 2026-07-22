# Hypothesis Agent

The first stage of Delphi's People Analytics multi-agent platform. Given an
organization, it autonomously searches the space of possible organizational
hypotheses and emits **one** high-value, non-obvious, structured hypothesis —
a `HypothesisPackage` — for downstream agents (statistics, visualization,
business consulting, recommendations) to consume. It does not analyze data,
run statistics, or talk to end users; see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
for the full design.

No organizational dataset exists yet, so every external dependency —
data sources, memory, embeddings, LLMs, feedback, downstream agents — sits
behind an interface (`ports/`) with a swappable adapter (`adapters/`). The
reference adapters are in-memory and offline (`MockLLMService`,
`HashEmbeddingService`) so the whole thing runs with zero network access and
zero API keys, out of the box.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python examples/run_local_demo.py   # full search loop, offline, no config needed
pytest                              # unit + integration tests, offline
```

## Using a real LLM

`.env` (gitignored, loaded automatically via `python-dotenv` whenever
`di/container.py` is imported, regardless of cwd) is already set up for the
SHL internal LiteLLM endpoint:

```bash
pip install -e ".[llm-litellm]"
```
```dotenv
# .env
HYPOTHESIS_AGENT__BACKENDS__LLM=litellm
LITELLM_API_BASE=https://labs.shl.com/llm-internal/
LITELLM_API_KEY=          # <- add your key
```

That's the only thing you need to fill in — `backends.llm` and the endpoint
are already active. `examples/run_local_demo.py` and the test suite ignore
this and force `MockLLMService` explicitly in code either way, so they stay
offline regardless of what's in `.env`; `hypothesis_agent.server` and any
direct `HypothesisAgent`/`build_dependencies()` use pick it up. If the
endpoint expects a specific model identifier (it may need an `openai/`
prefix or a gateway-specific name), also set `HYPOTHESIS_AGENT__LLM__MODEL`
— the default (`gpt-4.1-nano`) is a generic OpenAI-compatible guess, not
guaranteed to match your gateway's naming.

To revert to the offline mock: comment out `HYPOTHESIS_AGENT__BACKENDS__LLM`
in `.env`, or set it to `mock`.

**OpenAI directly** (alternative to LiteLLM):
```bash
pip install -e ".[llm-openai]"
# in .env: OPENAI_API_KEY=...
```
Then set `backends.llm: openai` and `backends.embedding: openai`.

## Running the live JSON-backed feed + local API

The Delphi frontend (`../index.html`) can display a *live*, growing feed of
generated hypotheses instead of the offline demo. See the top-level
[../README.md](../README.md#running-the-full-loop-live-hypothesis-feed) for
the full walkthrough; in short:

```bash
pip install -e ".[server]"
cd ..                          # the Delphi/ repo root — the server resolves
python -m hypothesis_agent.server   # sample_data/stories.json relative to cwd
```

This forces `historical_memory_repository`/`feedback_repository` to
`json_file` (`JsonHypothesisStore`, §11.1 of the architecture doc) regardless
of other config, and exposes `GET /api/stories`, `POST /api/stories/{id}/reaction`,
and `POST /api/generate` on `:8200`.

## Optional extras

| Extra | Enables | Notes |
|---|---|---|
| `llm-openai` | `OpenAILLMService`, `OpenAIEmbeddingService` | needs `OPENAI_API_KEY` |
| `llm-litellm` | `LiteLLMService` | needs `LITELLM_API_KEY` (+ `LITELLM_API_BASE` for a proxy) |
| `deep-agents` | `DeepAgentUnderstandingEngine` | requires Python ≥3.11 |
| `strands` | `StrandsCriticOrchestrator` | needs a configured Strands model provider |
| `server` | `hypothesis_agent.server` (FastAPI + uvicorn) | powers the live JSON-backed feed |

## Layout

See [docs/ARCHITECTURE.md §6](docs/ARCHITECTURE.md#6-repository-folder-structure)
for the full annotated repository structure and every other design section
(component diagrams, LangGraph state graph, class diagram, data contracts,
prompt/memory/search architecture, testing strategy, and the implementation
roadmap).
