# Investigation Pipeline

Turns a Hypothesis Agent `HypothesisPackage` into a full executive
`InsightPackage`: Investigation Planner → Data Retrieval → Analytics → Root
Cause Discovery → Business Insight → Narrative → Visualization Planner →
Plot Generation. See [../docs/PLATFORM_ARCHITECTURE.md](../docs/PLATFORM_ARCHITECTURE.md)
for the full design — this package implements phases 1-10 of its roadmap
(§23); the frontend Insight Report view and production-hardening phases
(11-12) are not yet built.

Depends on [`../hypothesis_agent`](../hypothesis_agent) (imports
`HypothesisPackage` and reuses its `LLMService`/`EmbeddingService`
ports/adapters — one LLM configuration for the whole platform, not two).
`hypothesis_agent` has zero knowledge this package exists.

## Quickstart

```bash
# hypothesis_agent must be installed first (editable, so this package can import it)
pip install -e ../hypothesis_agent

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,analytics,plotting,data-excel]"

python examples/run_investigation_demo.py   # full pipeline, offline (MockLLMService), real Book1.xlsx stats
pytest                                       # unit + integration tests, offline
```

## Using a real LLM

Reuses whatever `hypothesis_agent/.env` already has configured
(`backends.llm: litellm` + `LITELLM_API_KEY`/`LITELLM_API_BASE` — see
[../hypothesis_agent/README.md](../hypothesis_agent/README.md)). No separate
key or config needed here.

## Running the API

```bash
pip install -e ".[server]"
cd ..   # Delphi/ repo root — resolves Book1.xlsx and sample_data/insights.json
python -m insight_pipeline.server
```

Serves on `:8300`: `POST /api/investigate` (body: `{"hypothesis_package":
{...}}`, returns an insight package id), `GET /api/insights/{id}`,
`GET /api/insights`.

With the Hypothesis Agent API also running (`:8200`, see
[../hypothesis_agent/README.md](../hypothesis_agent/README.md)) and at
least one hypothesis already generated there, feed it into this API
end to end with:

```bash
python examples/run_investigation_from_server.py
```

## What's real vs. what's scaffolded

- **Real, computed, not mocked**: the four Analytics plugins (correlation,
  simple linear regression, one-way ANOVA, chi-square — real `scipy`
  against real `Book1.xlsx` rows), the five Plot Generation renderers (real
  `matplotlib` PNGs), the Excel `EmployeeDataRepository`, the whole
  orchestrator graph.
- **LLM-reasoned**: Investigation Planner, Query Planner, Root Cause
  Discovery, Business Insight, Narrative, Visualization Planner — all via
  `hypothesis_agent`'s `LLMService`, offline-testable via `MockLLMService`,
  meaningful output requires a real backend (see above).
- **Deep Agents variants** (`DeepAgentInvestigationPlanner`,
  `DeepAgentMechanismBrainstormPlugin`) are implemented but unverified in
  this environment — `deepagents` requires Python ≥3.11, same constraint as
  `hypothesis_agent`'s own Deep Agents adapter.
- **Strands variant** (`StrandsQueryPlanner`) is implemented and construction-
  verified (`strands-agents` installs and imports cleanly under Python
  3.10) but not exercised against a live model in this environment (no
  default Strands model provider credentials here).

## Layout

Mirrors `hypothesis_agent`'s shape: `contracts/`, `ports/`, `plugins/`
(analysis methods, root-cause strategies, business evaluators, narrative
strategies, visualization recommenders — all the Hypothesis Agent's own
`PluginRegistry` reused directly), `adapters/`, `agents/<name>/` (one
submodule per agent, each internally ports-only), `tools/plot_generation/`
(deterministic, no reasoning), `orchestrator/` (the top-level LangGraph),
`di/`, `server/`.
