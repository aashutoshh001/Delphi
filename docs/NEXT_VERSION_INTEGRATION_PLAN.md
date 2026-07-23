# Delphi Next Version — Integration Plan & Architecture

**Status:** Analysis + plan only. No code has been changed as a result of this
document. Written after a deep read of two external, pre-authorized codebases
(`/home/aashutosh.joshi/AI-Thon/Base-Agents-Strands` and
`/home/aashutosh.joshi/AI-Thon/team-onboarding`) to identify what can be
reused rather than rebuilt for Delphi's next version: real-database-backed,
column-aware hypothesis generation and deep multi-horizon investigation.

---

## 1. Executive summary

- **`team-onboarding`** is not a codebase — it's a single Claude Code *skill
  definition* (`SKILL.md`) that bootstraps a new repo's `CLAUDE.md`/`AGENTS.md`/
  `docs/` skeleton. Nothing in it is a reusable component for Delphi. It's
  noted here for completeness and then set aside.
- **`Base-Agents-Strands/base-agents-strands`** is the real find: a mature,
  production-shaped Strands-SDK multi-agent system ("Talent Intelligence")
  that already solves — for a sibling SHL product — almost exactly the
  problem Delphi's next version needs to solve: turn a natural-language
  question into a validated, scoped, read-only SQL query against a real
  MySQL table of SHL psychometric scores, then chart and narrate the result.
  It is architecturally distinct from Delphi (chat-turn-based MCP server vs.
  Delphi's one-shot hypothesis→investigation pipeline) but several of its
  *components* — the data spec, the SQL-safety pattern, the column-to-meaning
  prompt convention, the descriptive-stats builder — are directly portable.
- The single highest-value asset is
  **`docs/base_agents_scores_master_spec.md`**: a 183-column authoritative
  spec for `talent_db.base_agents_scores` (MySQL). Delphi's current
  `Book1.xlsx` (379 rows × 153 columns: 104 GSA sub-competencies + 20
  aggregate buckets + 2 HiPo scores + 27 Leader-Challenges fit percentiles)
  is a **structural subset of this exact same SHL data model** — same
  column-naming convention, same 1–5 scale, same GSA/OPQ/MQ/HiPo/Leader-
  Challenges families. This means the master spec is *already* the right
  column-semantics document for Delphi's real-database future, not
  something to write from scratch.
- Correction to an earlier assumption in this conversation: the 144 prompts
  found in the shared Langfuse project (`AMBIGUITY_RESOLUTION`,
  `COUNT_NL2SQL`, `employee_assessments/GSA/AI_Readiness/...`, etc.) are
  **not** from `base-agents-strands`. That codebase loads all its prompts
  from local `.md` files (`talent_intelligence/agent.py::load_local_prompt_ref`
  reads `prompts/TalentIntelligenceAgents/**`, never Langfuse). The Langfuse
  project is shared with a third, unrelated system. This plan treats
  `base-agents-strands`'s local prompt files as the reusable asset, not the
  Langfuse-hosted ones.

---

## 2. Deep analysis: `Base-Agents-Strands/base-agents-strands`

### 2.1 What it is

A FastMCP-based server exposing four chat agents (`succession_planning`,
`high_potential`, `enterprise_leader`, `skill_development`) over one MCP HTTP
endpoint. Each agent is a **Strands `Agent`** orchestrator that can call three
internal tools, each of which launches its own **specialist Strands
sub-`Agent`**:

```
{agent}_chat (MCP tool)
  -> orchestrator (Strands Agent, structured_output_model=OrchestratorPresentation)
       -> offer_competency_selection   (in-process tool, no sub-agent)
       -> nl2sql_subagent              (launches a Strands Agent with tool: execute_query)
       -> visualization_subagent       (launches a Strands Agent with tool: create_visualization)
       -> narrative_subagent           (launches a Strands Agent, no tools)
```

Results flow through a single mutable `analysis_state` dict shared across the
turn (not separate typed contracts per stage) — the subagents read and write
directly into it. Session/turn history and `analysis_context` persist in
MongoDB; the actual candidate data lives in **MySQL**, queried live per turn
via NL2SQL, never cached or duplicated into Mongo.

### 2.2 Tech stack (`requirements.txt`)

| Concern | Library |
|---|---|
| Agent orchestration | `strands-agents[openai]` |
| MCP server | `mcp`, `fastmcp[apps]` |
| Real candidate DB | `sqlalchemy` + `pymysql` (MySQL) |
| Session/state DB | `pymongo` (MongoDB) |
| Data shaping | `pandas` |
| Tracing | raw OpenTelemetry (`opentelemetry-sdk` + `OTLPSpanExporter`) → an external OTEL collector, which then fans out to Langfuse — **not** litellm's built-in callback (Delphi's current approach) |
| API layer | `fastapi` + `uvicorn` |
| AWS runtime memory | `bedrock-agentcore[strands-agents]` (managed short-term chat memory) |

### 2.3 The single most valuable asset: `docs/base_agents_scores_master_spec.md`

A 478-line authoritative data contract for `talent_db.base_agents_scores`
(MySQL 8), 183 columns, one row per candidate. Structure:

- **§1 Overview** — a table mapping each of 5 SHL assessment products (GSA,
  OPQ, Leader Challenges Personality, Leader Challenges Experience/`_xp`, MQ,
  HiPo) to column counts and *what it captures conceptually* (e.g. "GSA =
  self-reported current behaviour, stable 12–18mo" vs "OPQ = personality-
  derived potential, stable 3–5yr").
- **§2 Value scale & NULL semantics** — every score is 1–5, NULL means "not
  assessed" (never a sentinel), with an explicit load rule never to
  substitute `0`/`-1`/`999`.
- **§3 Column catalog** — all 183 columns, physical DB order, grouped into
  10 subsections, each with ordinal position, exact column name, and value
  range. Includes *why* families relate (e.g. "Leader Challenges Personality"
  = OPQ-derived *fit* for a challenge; the parallel `_xp` block = independent
  self-rated *experience* with that same challenge — a candidate can score
  high on one and low on the other).
- **§4 Load rules & invariants** — uniqueness assumptions, controlled
  vocabularies, byte-for-byte column-name matching requirements (NL2SQL
  breaks silently on drift), coverage expectations per assessment family
  (e.g. OPQ Leadership rollups ~86% populated — only candidates who took a
  specific module).
- **§5 Known quirks** — e.g. 5 of 8 Great-8 columns are `BIGINT`, 3 are
  `DOUBLE`, and the pattern is intentional/historical, not something to
  "clean up."

**Why this matters for Delphi specifically:** compare this to `Book1.xlsx`
(`hypothesis_agent/adapters/shl_sample_cohort.py`) — 379 candidates × 153
attributes: 104 granular behavioral indicators (0–5), 20 aggregate
competency buckets, 2 leadership-potential scores (Aspiration/Ability —
literally `HiPo_Aspiration_Score_Bucket` / `HiPo_Ability_Score_Bucket` in the
183-column table), and 27 role/context-fit percentiles (= the "Leader
Challenges — Personality" family). **`Book1.xlsx` is a same-schema sample of
this exact table**, just without the `_xp` experience block, MQ, and some
OPQ sub-detail. This means Delphi's next version doesn't need to invent a
column-semantics document — it needs to *consume* this one (or its
production successor once the real MySQL table exists), and Delphi's
existing `AttributeField`/`EmployeeDataLandscape` contracts already have the
right shape (`category`, `data_type`, `coverage_ratio`, `description`) to
hold this richer semantic data — they're just populated too thinly today
(generic categories like `"behavioural_competency"` instead of `"GSA
sub-competency of Leading & Deciding, self-reported current behaviour,
stable 12-18mo"`).

### 2.4 The SQL-safety pattern (`talent_intelligence/tools/nl2sql.py`)

This is the second most valuable asset — a real, load-bearing security
pattern Delphi's Investigation Pipeline currently has no equivalent of
(Delphi resolves data via column-name matching against an in-memory
DataFrame; it never generates or executes free-form SQL).

1. **Regex write-guard**: `_WRITE_OPERATION_PATTERN` rejects any query
   containing `insert|update|delete|drop|alter|create|truncate|replace|
   merge|call|load` as whole words, case-insensitive.
2. **Structural validation** (`_validate_select_query`): the query must
   start with `SELECT`, must **not** define its own `WITH` clause (the
   system injects one), must reference the injected subset name, and must
   **not** reference the physical source table directly.
3. **Population scoping via injected CTE** (`_build_candidate_subset_cte`):
   candidate IDs from the caller-supplied `groups` are turned into a
   `UNION ALL` of literal rows, joined against the real table, and
   prepended as a `WITH candidate_subset AS (...)` CTE. The model-generated
   SQL is *never* allowed to see or touch the real table name — only
   `candidate_subset`. If no group is selected, execution is refused
   outright ("No candidate group is selected for analysis.").
4. **Execution** (`_execute_mysql_query`): SQLAlchemy `create_engine(SQL_DB_URL)`,
   one connection, `text(final_sql)`, `finally: engine.dispose()`.
5. **Automatic result summarization** (`_build_descriptive_stats` +
   `_build_summary_from_records`): given *any* result set, groups by
   `Group_Label` if present, computes `pandas .describe()` for numeric
   columns and top-5 value counts for categorical columns, formats it as
   plain text for the next LLM call. This is a general-purpose "explain this
   query result" utility, decoupled from any specific statistical method —
   broader than Delphi's current four fixed `AnalysisMethodPlugin`s
   (correlation/regression/ANOVA/chi-square).

### 2.5 The competency-schema-as-prompt convention

`talent_intelligence/competency_schema.py::extract_competency_column_lines()`
is an 18-line function: it takes a markdown file like
`prompts/TalentIntelligenceAgents/Enterprise_Leader/CompetencySchema.md`
(format: `- ColumnName | type | range | description: ...`, one line per
column) and a list of selected competency names, and returns just the
matching lines. This is how the NL2SQL subagent's prompt gets told what each
requested column *means* without dumping the entire 183-column catalog into
every call. Directly adaptable: Delphi could maintain one such file per
category (or reuse the master spec directly) and inject only the
`AttributeField`s relevant to a given investigation.

### 2.6 Orchestration pattern worth adopting

`talent_intelligence/orchestrator.py::run_talent_intelligence_orchestrator`
shows a clean, real (non-fallback) Strands pattern Delphi currently only
uses as a secondary/optional backend:

- One `Agent(...)` with `tools=[offer_competency_selection, nl2sql_subagent,
  visualization_subagent, narrative_subagent]` and
  `structured_output_model=OrchestratorPresentation` — the orchestrator
  itself decides the route (`need_competency_selection` /
  `need_visualization` / `need_narrative` / `end_conversation`) rather than
  a hand-coded LangGraph edge sequence.
- `SummarizingConversationManager(summary_ratio=0.3, preserve_recent_messages=10,
  proactive_compression=True)` — automatic conversation-memory compression,
  something Delphi has no equivalent of (not needed yet, since Delphi is
  one-shot, but relevant once "in-depth analysis on different horizons" adds
  multiple sequential passes over the same hypothesis).
- `trace_attributes=_build_strands_trace_attributes(...)` passed straight
  into `Agent(...)` — Strands' own native tracing-attribute mechanism,
  parallel to (and potentially cleaner than) manually threading
  `metadata={"session_id": ...}` through every `LLMRequest` the way this
  session's Langfuse work just did for Delphi.
- A per-request `contextvars.ContextVar` (`_REQUEST_CONTEXT`) carrying
  `config`, `agent_config`, `candidate_groups`, `analysis_state`,
  `session_id` — read by every tool function without explicit parameter
  threading. This is how `execute_query`/`create_visualization` (both
  decorated `@tool`, called by an LLM, not by application code) get access
  to request-scoped state without it being part of the tool's LLM-visible
  signature.

### 2.7 Visualization: Chart.js config, not server-rendered images

`talent_intelligence/tools/visualization.py::VisualizationConfig` (Pydantic)
validates chart type (`bar`/`line`/`scatter`/`pie`/`histogram`/`table`/
`radar`/`box-plot-chart`/`experience_personality_chart`), axis columns,
optional `pandas`-`melt`-style reshaping (`value_vars`/`id_vars`/`var_name`/
`value_name` for wide-to-long transforms), and reference lines. The *client*
renders the chart from this JSON — the server never produces an image file.
This is architecturally different from Delphi's `MatplotlibPlottingEngine`
(server-rendered PNGs), and not something to blindly copy — Delphi's static
frontend serves flat files, so PNG generation is the right fit for the
*current* frontend. Worth knowing about only if Delphi's frontend evolves
into something more interactive.

`experience_personality_chart` is a bespoke type: `_assign_quadrants` in
`visualization_utils.py` buckets candidates into Invest/Leverage/Reconsider/
Redirect based on personality-fit vs. experience — a real example of a
domain-specific chart type layered on top of the generic chart config, worth
knowing as a pattern (domain-specific chart types as an escape hatch) even
though the specific quadrant logic is Succession-Planning-only.

### 2.8 What NOT to take

- **MCP server / chat-session architecture** (`mcp_app/server.py`,
  MongoDB session documents, `render_chart`/`render_narrative`/
  `competency_selection` pending-store pattern) — this solves a
  multi-turn-conversation problem Delphi doesn't have. Delphi's flow is
  one-shot (generate hypothesis → investigate → done), not a chat session
  the user drives turn-by-turn. Adopting this would be solving a problem
  Delphi doesn't have yet.
- **AWS Bedrock AgentCore memory integration** — infra-specific to that
  team's AWS deployment; Delphi has no AgentCore dependency and shouldn't
  acquire one just because this sibling system uses it.
- **`security/access_control.py`, `gateway-identity/`, Cognito JWT
  validation** — enterprise auth/multi-tenant concerns; out of scope for
  Delphi's current single-operator local-dev shape.
- **The specific business domains** (Succession Planning, High Potential,
  Enterprise Leader, Skill Development as *chat agents*) — these are
  products, not infrastructure. Delphi's hypothesis-generation "business
  lens" concept is a different, broader idea (discovering *which* question
  to ask, not answering a pre-selected one) and shouldn't be collapsed into
  these four.

---

## 3. Analysis: `team-onboarding`

One file, `SKILL.md` — a Claude Code skill that interactively asks 8
questions (project name, description, problem statement, language/framework,
deployment, HTTP API?, database?, AI/LLMs?) and generates `CLAUDE.md`,
`AGENTS.md`, and a `docs/` skeleton (`API_DOCS.md`, `ARCHITECTURE.md`,
`product-specs/`, `changelogs/`, `feature-log/`) from templates. It encodes a
specific team convention: every non-trivial change requires a
`docs/product-specs/<date>_<n>.md` written and committed *before* any code
change, plus mandatory `CLAUDE.md`/`AGENTS.md` updates after every change.

**Nothing here is a Delphi component.** It's a process/documentation
convention for onboarding *new, unrelated* repositories, not something with
data, agents, or analysis logic to integrate. Included in this plan only for
completeness, per the instruction to dig into both folders — there is no
follow-up action for it beyond noting that if Delphi's own docs discipline
ever needs tightening, this convention (spec-before-code, mandatory doc
sync) is a reasonable one to optionally adopt independently of any code
reuse.

---

## 4. What this means for Delphi's next version

Three things the user asked for, mapped to what was just found:

1. **"Real database access, and knowing what each column depicts from
   prompts"** → `base_agents_scores_master_spec.md` is that column-meaning
   document, already written, for the exact same SHL data model Delphi
   samples via `Book1.xlsx`. The NL2SQL safety pattern
   (`talent_intelligence/tools/nl2sql.py`) is the safe way to let an LLM
   query it once a real MySQL connection exists.
2. **"In-depth analysis on the hypothesis, complete database, fetching
   relevant information, different horizons/aspects, then plots and
   insights"** → this is structurally what Delphi's Investigation Pipeline
   *already* does (Investigation Planner → Data Retrieval → Analytics →
   Root Cause → Business Insight → Narrative → Visualization Planner → Plot
   Generation) — the gap is that it operates on a static Excel DataFrame
   with column-name matching, not a real, larger MySQL table with
   population-scoped, model-written SQL. `base-agents-strands` shows the
   concrete mechanics for that upgrade (candidate_subset CTE, read-only
   validation, `execute_query`-as-a-tool pattern) without needing to design
   it from scratch.
3. **"Organization context"** → the `Domain_Context.md` files (one read in
   full: `Succession_Planning/Domain_Context.md` — SHL's Leader Challenges
   model, why each metric exists, worked examples like the "Global
   Holdings CMO" scenario) are a template for the kind of *business*
   framing Delphi's `understand_organization` node currently only gets from
   a thin `OrganizationProfile.core_attributes` dict + column categories.
   These domain-context documents are prose explanations of *why a metric
   matters*, which is exactly the gap between "the agent knows a column
   exists" and "the agent knows a column is strategically important."

---

## 5. Proposed next-version architecture

### 5.1 New/changed components

```
hypothesis_agent/
  adapters/
    employee/
      mysql_repository.py          [NEW] EmployeeRepository backed by
                                    SQLAlchemy + real MySQL, replacing/
                                    supplementing shl_sample_cohort.py.
                                    Still schema-only at this layer — reads
                                    column names/types/coverage via
                                    information_schema + row-count queries,
                                    never row-level values (unchanged
                                    boundary from today).
    organization_knowledge/
      column_semantics_repository.py [NEW] Loads a master-spec-shaped
                                      document (YAML/JSON derived from
                                      base_agents_scores_master_spec.md's
                                      structure) and exposes per-column
                                      descriptions to enrich AttributeField
                                      objects — category, assessment family,
                                      stability window, coverage expectation.
  contracts/
    organization.py                [EXTEND] AttributeField gains optional
                                    fields: assessment_family, stability_note,
                                    coverage_expectation_pct — all optional,
                                    backward compatible, populated only when
                                    the column-semantics repository has data.

insight_pipeline/
  adapters/
    dataset_retrieval/
      sql_query_planner.py         [NEW] Parallel to DirectLLMQueryPlanner,
                                    but the LLM writes a validated SELECT
                                    against an injected population CTE,
                                    modeled directly on nl2sql.py's
                                    _validate_select_query +
                                    _build_candidate_subset_cte. Read-only
                                    by construction, same as the Langfuse
                                    MCP client's guardrail added this
                                    session — enforced in code, not
                                    trusted-by-convention.
      mysql_employee_data_repository.py [NEW] EmployeeDataRepository
                                    implementation executing that validated
                                    SQL via SQLAlchemy, parallel to
                                    ExcelEmployeeDataRepository.
    analytics/
      descriptive_stats_method.py  [NEW] AnalysisMethodPlugin wrapping the
                                    same pandas .describe()-per-group +
                                    top-N-categorical pattern from
                                    _build_descriptive_stats — a general
                                    "summarize whatever this query
                                    returned" method, complementing (not
                                    replacing) the four existing fixed
                                    statistical methods.
  config/
    settings.py                    [EXTEND] backends.employee_data_repository
                                    gains "mysql" alongside "excel" (existing
                                    plugin-registry pattern already supports
                                    this — no architecture change, just a new
                                    registry entry, matching how "excel" was
                                    added originally).
```

### 5.2 "Different horizons/aspects" — multi-pass investigation

Today, one `HypothesisPackage` produces exactly one `InsightPackage` via one
pass through the orchestrator graph. "In-depth analysis on different
horizons/aspects" implies running that same graph — or a subset of it
(Analytics → Root Cause → Business Insight) — multiple times against
different **population scopes** or **variable subsets** of the same
hypothesis, then merging results. Two concrete options, in order of
implementation cost:

- **Cheaper: parallel Analytics runs, one Investigation Plan.** Extend
  `AnalyticsAgent` to accept multiple `RetrievalQuery` scopes (e.g. "by
  tenure band", "by function", "by region" — a fixed set of standard
  cuts) and run the existing plugin registry against each concurrently
  (mirrors the existing `asyncio.gather` pattern in `AnalyticsAgent.run`
  and `_evaluation_helpers.run_evaluators`), merging into a
  `per_horizon_results: dict[str, AnalyticsResult]` field on
  `AnalyticsResult` or a new sibling contract.
- **More thorough: a real sub-graph.** A `horizons_node` between
  `investigation_planner` and `data_retrieval` that expands one
  `InvestigationPlan` into N `InvestigationPlan` variants (different
  population filters, different candidate variable subsets), runs the
  existing `data_retrieval → analytics → root_cause` chain once per variant
  (LangGraph supports this via `Send()` fan-out, already available since
  `langgraph>=0.6` is a pinned dependency), then a `merge_horizons_node`
  before `business_insight` combines cross-horizon findings — e.g.
  surfacing "this holds for EMEA but not APAC" as its own finding, which
  today's single-pass pipeline structurally cannot produce.

Either approach reuses 100% of the existing Analytics/Root-Cause/Business-
Insight contracts and plugin registries — this is additive breadth, not a
rewrite.

### 5.3 Column semantics feeding hypothesis generation

Today `EmployeeDataLandscape.available_fields` carries `category`/
`data_type`/`coverage_ratio`/`description`, all fairly thin
(`shl_sample_cohort.py`'s `_column_category()` returns one of four generic
category strings). With a `base_agents_scores_master_spec.md`-shaped
column-semantics source available, `AttributeField.description` can instead
carry the real per-column meaning ("OPQ-derived personality *fit* for
'Deliver Under High Uncertainty and Ambiguity' — independent of the
corresponding `_xp` self-rated *experience* column"), which directly
improves the Hypothesis Agent's `understand_organization` and
`generate_candidate` reasoning quality — it can propose hypotheses that
correctly reason about the *difference* between fit and experience, or
between current-behaviour (GSA) and stable-potential (OPQ), instead of
treating all numeric competency columns as interchangeable. This requires
zero change to the hard boundary rule (Hypothesis Agent never sees row-level
data) — column *semantics* are still schema-level metadata, not data.

### 5.4 Tracing upgrade path (optional, lower priority)

`base-agents-strands`'s raw-OTEL-to-collector approach
(`app/tracing.py`) is more standard/portable than Delphi's current
litellm-callback-based Langfuse integration (this session's work), but the
litellm callback is simpler and already working, tested, and read-only-
guardrailed. Not recommended as a near-term change — noted here only so a
future decision to standardize on OTEL isn't made without knowing this
sibling system's approach exists as prior art.

---

## 6. Execution plan / phased roadmap

| Phase | Deliverable | Depends on |
|---|---|---|
| **0** | This document (done) | — |
| **1** | Column-semantics repository: convert `base_agents_scores_master_spec.md`'s §3 catalog into a structured (YAML/JSON) source; extend `AttributeField`/`EmployeeDataLandscape` with optional semantic fields; wire into `shl_sample_cohort.py` so `Book1.xlsx`'s 153 columns get real descriptions today, before any DB migration | None — works against the existing Excel adapter immediately |
| **2** | MySQL `EmployeeRepository` (schema-only) for the Hypothesis Agent — same boundary as today, new backend | A real `SQL_DB_URL` to a `base_agents_scores`-shaped table (or equivalent) |
| **3** | `sql_query_planner.py` + `mysql_employee_data_repository.py` for the Investigation Pipeline, with the nl2sql.py-derived read-only/CTE-scoping guardrail | Phase 2's DB connection; can be built/tested against a read replica or a seeded dev MySQL instance independently of production access |
| **4** | Descriptive-stats general analysis method (`descriptive_stats_method.py`) | None — works today against the Excel-backed `DatasetHandle` too |
| **5** | Multi-horizon analysis (§5.2, cheaper option first) | Phase 3 (more valuable once population scoping is real, but not blocked by it — can be prototyped against Excel data first) |
| **6** | Domain-context documents (SHL Leader Challenges model, GSA/OPQ framing, etc., in the `Domain_Context.md` style) feeding `understand_organization` | Phase 1 |

Each phase is independently shippable and testable against Delphi's existing
offline/mock-backend discipline (`MockLLMService`, `HashEmbeddingService`) —
none of this requires a live MySQL connection to develop or unit-test
against; only Phase 3's true end-to-end integration test needs one.

---

## 7. Open questions for the user

1. Is there an actual `SQL_DB_URL`-reachable MySQL instance available for
   Delphi to target (the real `base_agents_scores` table, a copy of it, or a
   differently-named equivalent), or is Phase 2+ still speculative pending
   infrastructure access?
2. Should Delphi's column-semantics source be a **static converted copy** of
   `base_agents_scores_master_spec.md` (simple, no coupling to that repo),
   or should it **read the spec live** from that repo's `docs/` folder (stays
   in sync automatically, but couples Delphi's install to that repo's
   filesystem path)?
3. For multi-horizon analysis (§5.2): are there specific, known-important
   cuts (tenure, function, region, org unit) worth hard-coding as defaults,
   or should the Investigation Planner LLM propose horizons per-hypothesis?
