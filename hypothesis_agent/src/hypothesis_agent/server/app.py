"""Minimal local API backing the live hypothesis feed: serves the JSON store,
accepts reaction updates, and can trigger a new discover() run. This module
(like di/container.py) is allowed to hold a concrete `JsonHypothesisStore`
reference directly — it's an application entrypoint, not part of the
reasoning engine.

Run from the Delphi/ repo root (one level above hypothesis_agent/) so the
default relative `sample_data/stories.json` path resolves correctly:

    cd Delphi/
    python -m hypothesis_agent.server
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from hypothesis_agent.adapters.repositories.json_hypothesis_store import (
    JsonHypothesisStore,
)
from hypothesis_agent.agent import HypothesisAgent
from hypothesis_agent.config.settings import AgentConfig
from hypothesis_agent.contracts.memory import FeedbackRecord
from hypothesis_agent.contracts.organization import (
    AttributeField,
    EmployeeDataLandscape,
    OrganizationProfile,
)
from hypothesis_agent.di.container import build_dependencies
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.reasoning.dependencies import AgentDependencies

logger = get_logger("server")

ACME_DEMO_ORGANIZATION_ID = "acme-labs"


def _build_server_config() -> AgentConfig:
    config = AgentConfig.load()
    # The server's entire purpose is the live JSON-backed feed — force these
    # two backends regardless of whatever config/env is otherwise set.
    config.backends.historical_memory_repository = "json_file"
    config.backends.feedback_repository = "json_file"
    return config


def _seed_acme_demo_organization(deps: AgentDependencies) -> None:
    """A synthetic fallback organization — always available, no external file
    needed — so the offline MockLLMService demo path keeps working."""
    deps.organization_repository.add(
        OrganizationProfile(
            organization_id=ACME_DEMO_ORGANIZATION_ID,
            name="Acme Labs",
            core_attributes={
                "industry": "enterprise software",
                "headcount_band": "1000-5000",
                "business_goals": ["reduce regretted attrition", "scale engineering leadership bench"],
            },
        )
    )
    deps.employee_repository.add(
        EmployeeDataLandscape(
            organization_id=ACME_DEMO_ORGANIZATION_ID,
            employee_count_estimate=3200,
            available_fields=[
                AttributeField(name="performance_rating", category="performance", coverage_ratio=0.95),
                AttributeField(name="burnout_index", category="burnout", coverage_ratio=0.6),
                AttributeField(name="communication_competency", category="communication", coverage_ratio=0.7),
                AttributeField(name="tenure_months", category="tenure", coverage_ratio=1.0),
                AttributeField(name="leadership_competency", category="leadership", coverage_ratio=0.5),
                AttributeField(name="technical_competency", category="technical_competency", coverage_ratio=0.8),
                AttributeField(name="promotion_last_18mo", category="promotion", coverage_ratio=1.0),
            ],
        )
    )


def _seed_shl_sample_cohort(deps: AgentDependencies) -> str | None:
    """Real sample data (Book1.xlsx, 378 candidates x 153 SHL competency/
    psychometric attributes), loaded as schema-level landscape info only —
    see adapters/shl_sample_cohort.py. Returns the organization_id if the
    file was found and loaded, else None (server still starts, falls back
    to the synthetic Acme Labs org)."""
    from hypothesis_agent.adapters.shl_sample_cohort import (
        load_organization_and_landscape,
    )

    try:
        profile, landscape = load_organization_and_landscape()
    except FileNotFoundError:
        logger.warning(
            "Book1.xlsx not found (expected at repo root) — "
            "skipping the real sample cohort, only Acme Labs demo data is available"
        )
        return None
    except ImportError:
        logger.warning(
            "openpyxl not installed (pip install hypothesis_agent[sample-data]) — "
            "skipping the real sample cohort, only Acme Labs demo data is available"
        )
        return None
    deps.organization_repository.add(profile)
    deps.employee_repository.add(landscape)
    return profile.organization_id


_config = _build_server_config()
_deps = build_dependencies(_config)
_seed_acme_demo_organization(_deps)
_shl_cohort_id = _seed_shl_sample_cohort(_deps)
DEFAULT_ORGANIZATION_ID = _shl_cohort_id or ACME_DEMO_ORGANIZATION_ID
_agent = HypothesisAgent(_deps)
_store = JsonHypothesisStore(_config.backends.json_store_path, _deps.embedding_service)

logger.info(
    "hypothesis agent server starting",
    extra={
        "extra_fields": {
            "json_store_path": str(Path(_config.backends.json_store_path).resolve()),
            "llm_backend": _config.backends.llm,
        }
    },
)

app = FastAPI(title="Delphi Hypothesis Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReactionUpdate(BaseModel):
    reaction: Literal["up", "down", "none"]


class GenerateRequest(BaseModel):
    organization_id: str = DEFAULT_ORGANIZATION_ID


class InsightReferenceUpdate(BaseModel):
    insight_package_id: str


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/stories")
async def get_stories() -> list[dict]:
    return await _store.list_raw()


@app.post("/api/stories/{story_id}/reaction")
async def set_reaction(story_id: str, body: ReactionUpdate) -> dict:
    try:
        await _store.record_feedback(FeedbackRecord(hypothesis_id=story_id, signal=body.reaction))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="story not found") from exc
    return {"ok": True}


@app.post("/api/stories/{story_id}/insight")
async def set_insight_reference(story_id: str, body: InsightReferenceUpdate) -> dict:
    """Called by the frontend once it has separately run this story's
    hypothesis through the Investigation Pipeline API (:8300) — records the
    resulting InsightPackage id so "Read more" can link straight to the full
    report next time. This package never calls insight_pipeline itself
    (that boundary is deliberate); it just remembers an opaque id handed to
    it by whoever did."""
    found = await _store.set_insight_reference(story_id, body.insight_package_id)
    if not found:
        raise HTTPException(status_code=404, detail="story not found")
    return {"ok": True}


@app.post("/api/generate")
async def generate(body: GenerateRequest) -> dict:
    logger.info("generate requested", extra={"extra_fields": {"organization_id": body.organization_id}})
    try:
        package = await _agent.discover(body.organization_id)
    except RuntimeError as exc:
        # The search loop's hard dedup guarantee (never store a near-duplicate
        # of an existing hypothesis) can legitimately exhaust every candidate
        # in a run once enough hypotheses already exist for this organization.
        # That's expected behavior, not a server fault — surface it as a
        # normal 409 with an actionable message instead of a raw 500.
        raise HTTPException(
            status_code=409,
            detail=(
                "No new hypothesis found this run — every candidate was "
                "rejected as a near-duplicate of one already stored, or "
                "scored too low. Try again (search is randomized), or "
                f"increase search.max_iterations. ({exc})"
            ),
        ) from exc
    return {
        "package_id": package.package_id,
        "headline": package.headline,
        "summary": package.summary,
        "hypothesis_statement": package.hypothesis_statement,
        "business_lens": package.business_lens,
        "composite_score": package.scorecard.composite,
    }
